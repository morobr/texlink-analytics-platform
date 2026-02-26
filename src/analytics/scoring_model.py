"""
Oficina Quality Scoring Model — Texlink Analytics Platform

Weighted multi-dimensional composite scoring with configurable weights.
Mirrors and extends the logic in marts_oficina_scoring.sql.

Dimensions (0-10 scale each):
    1. Qualidade    — quality ratings             (default 30%)
    2. Pontualidade — on-time delivery            (default 25%)
    3. Comunicacao  — communication ratings       (default 15%)
    4. Experiencia  — order volume / history      (default 15%)
    5. Certificacoes — workshop certifications    (default 10%)
    6. Velocidade   — proposal response speed     (default  5%)
"""

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text

load_dotenv()


@dataclass
class ScoringWeights:
    """
    Weight configuration for the composite score.
    All weights must sum to 1.0 (±0.001 tolerance).
    """

    qualidade: float = 0.30
    pontualidade: float = 0.25
    comunicacao: float = 0.15
    experiencia: float = 0.15
    certificacoes: float = 0.10
    velocidade: float = 0.05

    def __post_init__(self) -> None:
        total = sum(vars(self).values())
        if not np.isclose(total, 1.0, atol=0.001):
            raise ValueError(f"Weights must sum to 1.0, got {total:.4f}")

    def as_dict(self) -> dict:
        return {k: v for k, v in vars(self).items()}


class OficinaScorer:
    """
    Multi-dimensional Oficina quality scoring engine.

    Usage:
        scorer = OficinaScorer()
        ranked = scorer.get_ranked_oficinas(estado="SC")
        detail = scorer.explain_score("oficina-uuid")
    """

    RANKING_TIERS = {
        "elite": (8.5, 10.0),
        "premium": (7.0, 8.5),
        "standard": (5.0, 7.0),
        "basico": (0.0, 5.0),
    }

    def __init__(self, engine=None, weights: Optional[ScoringWeights] = None):
        if engine is None:
            db_url = os.getenv(
                "DATABASE_URL", "postgresql://texlink:password@localhost:5432/texlink"
            )
            engine = create_engine(db_url)
        self.engine = engine
        self.weights = weights or ScoringWeights()

    # ──────────────────────────────────────────────
    # Data loading
    # ──────────────────────────────────────────────

    def _load_performance_data(self) -> pd.DataFrame:
        """Load int_oficina_performance data."""
        query = text("""
            SELECT
                oficina_id,
                nome_fantasia,
                estado,
                cidade,
                tier,
                capacidade_mensal_pecas,
                total_pedidos,
                pedidos_finalizados,
                total_avaliacoes,
                nota_qualidade_media,
                nota_pontualidade_media,
                nota_comunicacao_media,
                score_qualidade_media,
                score_pontualidade_media,
                score_comunicacao_media,
                win_rate_pct,
                taxa_aprovacao_media_pct,
                pct_entrega_no_prazo,
                tempo_medio_resposta_h,
                total_certificacoes,
                score_certificacoes,
                tem_abvtex,
                tem_cert_premium,
                ativo_recente
            FROM int_oficina_performance
        """)
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        logger.info(f"Loaded performance data for {len(df)} oficinas")
        return df

    # ──────────────────────────────────────────────
    # Dimension scorers (static, 0-10 output)
    # ──────────────────────────────────────────────

    @staticmethod
    def _score_qualidade(row: pd.Series) -> float:
        """Quality: use live ratings if ≥3 reviews, else fall back to stored score."""
        if row.get("total_avaliacoes", 0) >= 3 and pd.notna(row.get("nota_qualidade_media")):
            return float(row["nota_qualidade_media"]) * 2.0  # 1-5 → 2-10
        if pd.notna(row.get("score_qualidade_media")):
            return float(row["score_qualidade_media"]) * 2.0  # 0-5 → 0-10
        return 6.0  # neutral default

    @staticmethod
    def _score_pontualidade(row: pd.Series) -> float:
        """Reliability / on-time delivery."""
        if row.get("total_avaliacoes", 0) >= 3 and pd.notna(row.get("nota_pontualidade_media")):
            return float(row["nota_pontualidade_media"]) * 2.0
        if pd.notna(row.get("score_pontualidade_media")):
            return float(row["score_pontualidade_media"]) * 2.0
        return 6.0

    @staticmethod
    def _score_comunicacao(row: pd.Series) -> float:
        """Communication / responsiveness."""
        if row.get("total_avaliacoes", 0) >= 3 and pd.notna(row.get("nota_comunicacao_media")):
            return float(row["nota_comunicacao_media"]) * 2.0
        if pd.notna(row.get("score_comunicacao_media")):
            return float(row["score_comunicacao_media"]) * 2.0
        return 6.0

    @staticmethod
    def _score_experiencia(row: pd.Series) -> float:
        """Experience: total_pedidos normalized to 0-10 (50+ orders → 10)."""
        total = float(row.get("total_pedidos", 0) or 0)
        return min(10.0, total / 5.0)  # 0→0, 25→5, 50→10

    @staticmethod
    def _score_certificacoes(row: pd.Series) -> float:
        """Certifications: score_certificacoes normalized to 0-10."""
        cert = float(row.get("score_certificacoes", 0) or 0)
        return min(10.0, cert * 2.0)  # assumes max cert score ~5

    @staticmethod
    def _score_velocidade(row: pd.Series) -> float:
        """Response speed: faster → higher score (0-10)."""
        hours = row.get("tempo_medio_resposta_h")
        if pd.isna(hours) or hours is None:
            return 5.0  # neutral
        if hours <= 1:
            return 10.0
        if hours <= 4:
            return 8.0
        if hours <= 12:
            return 6.0
        if hours <= 24:
            return 4.0
        return 2.0

    @staticmethod
    def _assign_tier(score: float) -> str:
        if score >= 8.5:
            return "elite"
        if score >= 7.0:
            return "premium"
        if score >= 5.0:
            return "standard"
        return "basico"

    # ──────────────────────────────────────────────
    # Core scoring
    # ──────────────────────────────────────────────

    def compute_scores(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Compute composite quality score for all oficinas.

        Returns DataFrame with dimension scores, composite score (0-10),
        ranking tier, and percentile rank.
        """
        if df is None:
            df = self._load_performance_data()

        w = self.weights
        df = df.copy()

        df["score_qualidade"] = df.apply(self._score_qualidade, axis=1)
        df["score_pontualidade"] = df.apply(self._score_pontualidade, axis=1)
        df["score_comunicacao"] = df.apply(self._score_comunicacao, axis=1)
        df["score_experiencia"] = df.apply(self._score_experiencia, axis=1)
        df["score_certificacoes"] = df.apply(self._score_certificacoes, axis=1)
        df["score_velocidade"] = df.apply(self._score_velocidade, axis=1)

        df["score_composto"] = (
            df["score_qualidade"] * w.qualidade
            + df["score_pontualidade"] * w.pontualidade
            + df["score_comunicacao"] * w.comunicacao
            + df["score_experiencia"] * w.experiencia
            + df["score_certificacoes"] * w.certificacoes
            + df["score_velocidade"] * w.velocidade
        ).round(2)

        df["ranking_tier"] = df["score_composto"].map(self._assign_tier)
        df["percentil_rank"] = df["score_composto"].rank(pct=True).mul(100).round(1)

        output_cols = [
            "oficina_id", "nome_fantasia", "estado", "cidade", "tier",
            "capacidade_mensal_pecas", "total_pedidos", "total_avaliacoes",
            "score_qualidade", "score_pontualidade", "score_comunicacao",
            "score_experiencia", "score_certificacoes", "score_velocidade",
            "score_composto", "ranking_tier", "percentil_rank",
            "win_rate_pct", "pct_entrega_no_prazo", "tempo_medio_resposta_h",
            "tem_abvtex", "tem_cert_premium", "ativo_recente",
        ]
        available = [c for c in output_cols if c in df.columns]
        return (
            df[available]
            .sort_values("score_composto", ascending=False)
            .reset_index(drop=True)
        )

    # ──────────────────────────────────────────────
    # Convenience methods
    # ──────────────────────────────────────────────

    def get_ranked_oficinas(
        self,
        estado: Optional[str] = None,
        min_score: float = 0.0,
        limit: int = 50,
        df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Return top-ranked oficinas with optional filters.

        Args:
            estado:    Filter by state (e.g., 'SC', 'SP', 'CE').
            min_score: Minimum composite score threshold.
            limit:     Maximum rows returned.
            df:        Optional raw performance DataFrame.
        """
        scored = self.compute_scores(df)
        if estado:
            scored = scored[scored["estado"] == estado]
        scored = scored[scored["score_composto"] >= min_score]
        return scored.head(limit).reset_index(drop=True)

    def explain_score(
        self, oficina_id: str, df: Optional[pd.DataFrame] = None
    ) -> dict:
        """
        Return a detailed score breakdown for a single oficina.

        Returns dict with dimension scores, weights, weighted contributions, and total.

        Raises:
            ValueError: if oficina_id is not found in the scored data.
        """
        scored = self.compute_scores(df)
        match = scored[scored["oficina_id"] == oficina_id]
        if match.empty:
            raise ValueError(f"Oficina '{oficina_id}' not found in scored data")

        row = match.iloc[0]
        w = self.weights.as_dict()
        dims = ["qualidade", "pontualidade", "comunicacao", "experiencia", "certificacoes", "velocidade"]

        breakdown = {}
        for dim in dims:
            raw = float(row.get(f"score_{dim}", 0.0))
            weight = w[dim]
            breakdown[dim] = {
                "score": round(raw, 2),
                "weight": weight,
                "contribution": round(raw * weight, 3),
            }

        return {
            "oficina_id": oficina_id,
            "nome_fantasia": row.get("nome_fantasia"),
            "score_composto": float(row.get("score_composto", 0)),
            "ranking_tier": row.get("ranking_tier"),
            "percentil_rank": float(row.get("percentil_rank", 0)),
            "dimensions": breakdown,
        }

    def compare_weights(
        self,
        alt_weights: ScoringWeights,
        df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Compare how rankings change under an alternative weight configuration.

        Returns DataFrame with rank_current, rank_alt, and rank_delta per oficina.
        """
        raw = self._load_performance_data() if df is None else df

        scores_a = self.compute_scores(raw)[["oficina_id", "score_composto"]].rename(
            columns={"score_composto": "score_current"}
        )
        scorer_b = OficinaScorer(self.engine, alt_weights)
        scores_b = scorer_b.compute_scores(raw)[["oficina_id", "score_composto"]].rename(
            columns={"score_composto": "score_alt"}
        )

        merged = scores_a.merge(scores_b, on="oficina_id")
        merged["score_delta"] = (merged["score_alt"] - merged["score_current"]).round(3)
        merged["rank_current"] = merged["score_current"].rank(ascending=False).astype(int)
        merged["rank_alt"] = merged["score_alt"].rank(ascending=False).astype(int)
        merged["rank_delta"] = merged["rank_current"] - merged["rank_alt"]
        return merged.sort_values("rank_delta", ascending=False).reset_index(drop=True)

    def get_tier_distribution(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Count and percentage of oficinas in each ranking tier."""
        scored = self.compute_scores(df)
        tier_order = ["elite", "premium", "standard", "basico"]
        counts = scored["ranking_tier"].value_counts().reindex(tier_order, fill_value=0)
        total = len(scored)
        result = pd.DataFrame(
            {
                "ranking_tier": counts.index,
                "n_oficinas": counts.values,
                "pct": (counts.values / total * 100).round(1),
            }
        )
        return result.reset_index(drop=True)
