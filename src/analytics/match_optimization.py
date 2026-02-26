"""
Match Optimization — Texlink Analytics Platform

Supply-demand matching optimizer using compatibility scoring + Hungarian algorithm.

Approach:
    1. Load open pedidos (unmatched, published orders)
    2. Load available oficinas (active, with capacity and scoring data)
    3. Build N×M compatibility matrix (score per pedido-oficina pair)
    4. Run Hungarian algorithm for globally optimal assignment
    5. Return recommendations and supply/demand gap analysis
"""

import os
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from scipy.optimize import linear_sum_assignment
from sqlalchemy import create_engine, text

load_dotenv()

# State → geographic region mapping (simplified)
_STATE_REGION: dict[str, str] = {
    "SC": "sul", "PR": "sul", "RS": "sul",
    "SP": "sudeste", "RJ": "sudeste", "MG": "sudeste", "ES": "sudeste",
    "CE": "nordeste", "BA": "nordeste", "PE": "nordeste",
    "PA": "norte", "AM": "norte",
    "DF": "centro-oeste", "GO": "centro-oeste", "MT": "centro-oeste",
}


class MatchOptimizer:
    """
    Empresa↔Oficina matching optimizer.

    Usage:
        optimizer = MatchOptimizer()
        recs = optimizer.get_recommendations(pedido_id="some-uuid", top_n=5)
        assignments = optimizer.optimize_matching()
        gaps = optimizer.get_supply_demand_gaps()
    """

    # Compatibility score weights
    W_QUALITY = 0.30
    W_PUNCTUALITY = 0.25
    W_GEO = 0.20
    W_CAPACITY = 0.15
    W_SPEED = 0.10

    def __init__(self, engine=None):
        if engine is None:
            db_url = os.getenv(
                "DATABASE_URL", "postgresql://texlink:password@localhost:5432/texlink"
            )
            engine = create_engine(db_url)
        self.engine = engine

    # ──────────────────────────────────────────────
    # Data loading
    # ──────────────────────────────────────────────

    def _load_open_pedidos(self) -> pd.DataFrame:
        """Load unmatched, published orders."""
        query = text("""
            SELECT
                p.pedido_id,
                p.empresa_id,
                p.categoria_id,
                p.quantidade_total,
                p.valor_estimado,
                p.estado_preferencia,
                e.estado       AS empresa_estado,
                e.segmento     AS empresa_segmento,
                e.porte        AS empresa_porte
            FROM stg_pedidos p
            JOIN stg_empresas e ON p.empresa_id = e.empresa_id
            WHERE p.status_atual = 'publicado'
              AND NOT p.foi_matched
              AND NOT p.foi_cancelado
        """)
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        logger.info(f"Open pedidos: {len(df)}")
        return df

    def _load_available_oficinas(self) -> pd.DataFrame:
        """Load active oficinas with scoring and capacity data."""
        query = text("""
            SELECT
                o.oficina_id,
                o.estado,
                o.cidade,
                o.capacidade_mensal_pecas,
                o.score_medio,
                o.score_qualidade,
                o.score_pontualidade,
                o.win_rate_pct,
                o.pct_entrega_no_prazo,
                o.tempo_medio_resposta_h,
                o.tem_abvtex,
                o.tem_cert_premium,
                o.tier
            FROM int_oficina_performance o
            WHERE o.ativo_recente
        """)
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        logger.info(f"Available oficinas: {len(df)}")
        return df

    # ──────────────────────────────────────────────
    # Scoring helpers
    # ──────────────────────────────────────────────

    @staticmethod
    def _geo_score(pedido_estado: str, oficina_estado: str) -> float:
        """Geographic compatibility score [0, 1]."""
        if not pedido_estado or not oficina_estado:
            return 0.5
        if pedido_estado == oficina_estado:
            return 1.0
        p_region = _STATE_REGION.get(pedido_estado, "")
        o_region = _STATE_REGION.get(oficina_estado, "")
        if p_region and p_region == o_region:
            return 0.8
        return 0.5

    @staticmethod
    def _capacity_score(quantidade: float, capacidade: float) -> float:
        """
        Capacity fit score [0, 1].

        Rewards oficinas where the order fills 30-70% of monthly capacity.
        Penalizes heavy over-utilisation or severe under-utilisation.
        """
        if not capacidade or capacidade <= 0:
            return 0.0
        ratio = quantidade / capacidade
        if ratio <= 0.10:
            return 0.4  # too small for oficina
        if ratio <= 0.30:
            return 0.7
        if ratio <= 0.70:
            return 1.0  # sweet spot
        if ratio <= 1.00:
            return 0.7  # near full capacity
        return 0.2  # over capacity

    @staticmethod
    def _normalize_series(series: pd.Series, invert: bool = False) -> pd.Series:
        """Min-max normalize a series to [0, 1]."""
        mn, mx = series.min(), series.max()
        if mx == mn:
            return pd.Series(np.ones(len(series)), index=series.index)
        normalized = (series - mn) / (mx - mn)
        return 1.0 - normalized if invert else normalized

    # ──────────────────────────────────────────────
    # Compatibility matrix
    # ──────────────────────────────────────────────

    def build_compatibility_matrix(
        self,
        pedidos: Optional[pd.DataFrame] = None,
        oficinas: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Build N×M compatibility matrix (pedidos × oficinas).

        Each cell = weighted score in [0, 1] combining:
            quality (30%) + punctuality (25%) + geo (20%) + capacity (15%) + speed (10%)

        Returns:
            Long-format DataFrame: pedido_id, oficina_id, score, and sub-scores.
        """
        if pedidos is None:
            pedidos = self._load_open_pedidos()
        if oficinas is None:
            oficinas = self._load_available_oficinas()

        if pedidos.empty or oficinas.empty:
            logger.warning("No open pedidos or available oficinas — empty matrix")
            return pd.DataFrame()

        # Normalize oficina quality and speed to [0,1] across all oficinas
        oficinas = oficinas.copy()
        oficinas["_q"] = self._normalize_series(oficinas["score_qualidade"].fillna(3.0))
        oficinas["_p"] = self._normalize_series(oficinas["score_pontualidade"].fillna(3.0))
        oficinas["_spd"] = self._normalize_series(
            oficinas["tempo_medio_resposta_h"].fillna(24.0), invert=True
        )

        rows = []
        for _, pedido in pedidos.iterrows():
            qty = float(pedido.get("quantidade_total") or 100)
            p_estado = str(pedido.get("estado_preferencia") or pedido.get("empresa_estado") or "")

            for _, of in oficinas.iterrows():
                geo = self._geo_score(p_estado, str(of["estado"]))
                cap = self._capacity_score(qty, float(of["capacidade_mensal_pecas"] or 0))
                score = (
                    float(of["_q"]) * self.W_QUALITY
                    + float(of["_p"]) * self.W_PUNCTUALITY
                    + geo * self.W_GEO
                    + cap * self.W_CAPACITY
                    + float(of["_spd"]) * self.W_SPEED
                )
                rows.append(
                    {
                        "pedido_id": pedido["pedido_id"],
                        "oficina_id": of["oficina_id"],
                        "score": round(score, 4),
                        "geo_score": round(geo, 3),
                        "capacity_score": round(cap, 3),
                        "quality_score": round(float(of["_q"]), 3),
                        "punctuality_score": round(float(of["_p"]), 3),
                        "speed_score": round(float(of["_spd"]), 3),
                        "oficina_estado": of["estado"],
                        "oficina_tier": of["tier"],
                    }
                )

        logger.info(
            f"Compatibility matrix: {len(pedidos)} pedidos × {len(oficinas)} oficinas = {len(rows)} pairs"
        )
        return pd.DataFrame(rows)

    # ──────────────────────────────────────────────
    # Recommendations
    # ──────────────────────────────────────────────

    def get_recommendations(
        self,
        pedido_id: Optional[str] = None,
        top_n: int = 5,
        compat_matrix: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Return top-N recommended oficinas per pedido.

        Args:
            pedido_id:     Filter to a specific pedido. If None, returns all pedidos.
            top_n:         Number of recommendations per pedido.
            compat_matrix: Pre-built compatibility matrix (optional).

        Returns:
            DataFrame ranked by score descending.
        """
        matrix = compat_matrix if compat_matrix is not None else self.build_compatibility_matrix()
        if matrix.empty:
            return pd.DataFrame()

        if pedido_id:
            matrix = matrix[matrix["pedido_id"] == pedido_id]

        return (
            matrix.sort_values("score", ascending=False)
            .groupby("pedido_id", group_keys=False)
            .head(top_n)
            .reset_index(drop=True)
        )

    # ──────────────────────────────────────────────
    # Global optimal assignment
    # ──────────────────────────────────────────────

    def optimize_matching(
        self,
        pedidos: Optional[pd.DataFrame] = None,
        oficinas: Optional[pd.DataFrame] = None,
        compat_matrix: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Globally optimal pedido↔oficina assignment via Hungarian algorithm.

        Maximises total compatibility score across all assignments (one oficina
        can serve multiple pedidos; a pedido gets exactly one oficina assignment).

        Returns:
            DataFrame: pedido_id, oficina_id_optimal, compatibility_score, rank_in_available.
        """
        if compat_matrix is None:
            compat_matrix = self.build_compatibility_matrix(pedidos, oficinas)
        if compat_matrix.empty:
            return pd.DataFrame()

        pivot = compat_matrix.pivot_table(
            index="pedido_id",
            columns="oficina_id",
            values="score",
            aggfunc="first",
        ).fillna(0)

        pedido_ids = pivot.index.tolist()
        oficina_ids = pivot.columns.tolist()
        cost_matrix = -pivot.values  # negate for minimization (scipy minimises)

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        assignments = []
        for r, c in zip(row_ind, col_ind):
            pid = pedido_ids[r]
            oid = oficina_ids[c]
            score = float(pivot.iloc[r, c])

            # Rank of this oficina among all options for this pedido
            pedido_options = (
                compat_matrix[compat_matrix["pedido_id"] == pid]
                .sort_values("score", ascending=False)
                .reset_index(drop=True)
            )
            rank_matches = pedido_options[pedido_options["oficina_id"] == oid].index
            rank = int(rank_matches[0]) + 1 if len(rank_matches) > 0 else None

            assignments.append(
                {
                    "pedido_id": pid,
                    "oficina_id_optimal": oid,
                    "compatibility_score": round(score, 4),
                    "rank_in_available": rank,
                }
            )

        result = pd.DataFrame(assignments)
        top3_pct = (result["rank_in_available"] <= 3).mean() * 100
        logger.info(
            f"Optimal matching: {len(result)} assignments | "
            f"avg score={result['compatibility_score'].mean():.3f} | "
            f"top-3 choice={top3_pct:.1f}%"
        )
        return result

    # ──────────────────────────────────────────────
    # Supply-demand gap analysis
    # ──────────────────────────────────────────────

    def get_supply_demand_gaps(self) -> pd.DataFrame:
        """
        Identify states where demand outpaces local supply.

        Returns DataFrame: estado, n_open_pedidos, n_local_oficinas,
                           capacidade_total, supply_ratio, gap_score (0-100).

        Higher gap_score = more underserved (supply < demand).
        """
        pedidos = self._load_open_pedidos()
        oficinas = self._load_available_oficinas()

        demand = pedidos.groupby("empresa_estado").size().rename("n_open_pedidos")
        supply = oficinas.groupby("estado").size().rename("n_local_oficinas")
        capacity = (
            oficinas.groupby("estado")["capacidade_mensal_pecas"]
            .sum()
            .rename("capacidade_total")
        )

        gaps = (
            demand.rename_axis("estado")
            .to_frame()
            .join(supply, how="outer")
            .join(capacity, how="outer")
            .fillna(0)
            .reset_index()
        )

        gaps["supply_ratio"] = (
            gaps["n_local_oficinas"] / (gaps["n_open_pedidos"] + 1)
        ).round(3)
        gaps["gap_score"] = ((1 - gaps["supply_ratio"].clip(0, 1)) * 100).round(1)

        return gaps.sort_values("gap_score", ascending=False).reset_index(drop=True)
