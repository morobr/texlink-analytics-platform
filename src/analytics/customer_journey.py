"""
Customer Journey Analysis — Texlink Analytics Platform

Funnel analysis engine: signup → activation → match → conversion → retention
Reads from int_funnel_stages view.
"""

import os
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text

load_dotenv()


class CustomerJourneyAnalyzer:
    """Analyzes empresa customer journey through the Texlink acquisition funnel."""

    STAGES = ["registered", "activated", "matched", "converted", "retained"]
    STAGE_LABELS = {
        "registered": "Cadastrado",
        "activated": "Ativado (1º pedido publicado)",
        "matched": "Matched (proposta aceita)",
        "converted": "Convertido (pedido finalizado)",
        "retained": "Retido (2º+ pedido)",
    }

    def __init__(self, engine=None):
        if engine is None:
            db_url = os.getenv(
                "DATABASE_URL", "postgresql://texlink:password@localhost:5432/texlink"
            )
            engine = create_engine(db_url)
        self.engine = engine

    def _load_funnel_data(self) -> pd.DataFrame:
        """Load funnel stage data from int_funnel_stages view."""
        query = text("""
            SELECT
                empresa_id,
                segmento,
                porte,
                estado,
                current_stage,
                stage_num,
                dias_signup_para_ativacao,
                dias_ativacao_para_match,
                dias_match_para_conversao,
                dias_conversao_para_retencao,
                cohort_mes,
                total_pedidos,
                gmv_total
            FROM int_funnel_stages
        """)
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        logger.info(f"Loaded {len(df)} empresa funnel records")
        return df

    def get_funnel_summary(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Build top-level funnel: count and conversion rate at each stage.

        Returns DataFrame with columns:
            stage, stage_label, count, pct_of_top, conversion_from_prev
        """
        if df is None:
            df = self._load_funnel_data()

        records = []
        for i, stage in enumerate(self.STAGES):
            stage_num = i + 1
            count = int((df["stage_num"] >= stage_num).sum())
            records.append(
                {"stage": stage, "stage_label": self.STAGE_LABELS[stage], "count": count}
            )

        funnel = pd.DataFrame(records)
        top = funnel.loc[0, "count"]
        funnel["pct_of_top"] = (funnel["count"] / top * 100).round(1)
        funnel["conversion_from_prev"] = (
            funnel["count"] / funnel["count"].shift(1) * 100
        ).round(1)
        return funnel

    def get_time_to_convert(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Median days between each funnel stage transition.

        Returns DataFrame with stage transitions and median/p25/p75 days.
        """
        if df is None:
            df = self._load_funnel_data()

        time_cols = {
            "signup → ativação": "dias_signup_para_ativacao",
            "ativação → match": "dias_ativacao_para_match",
            "match → conversão": "dias_match_para_conversao",
            "conversão → retenção": "dias_conversao_para_retencao",
        }

        records = []
        for label, col in time_cols.items():
            vals = df[col].dropna()
            records.append(
                {
                    "transicao": label,
                    "n": len(vals),
                    "mediana_dias": round(vals.median(), 1) if len(vals) > 0 else None,
                    "p25_dias": round(vals.quantile(0.25), 1) if len(vals) > 0 else None,
                    "p75_dias": round(vals.quantile(0.75), 1) if len(vals) > 0 else None,
                    "media_dias": round(vals.mean(), 1) if len(vals) > 0 else None,
                }
            )

        return pd.DataFrame(records)

    def get_funnel_by_segment(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Funnel conversion rates broken down by empresa segment."""
        if df is None:
            df = self._load_funnel_data()

        records = []
        for segment, group in df.groupby("segmento"):
            total = len(group)
            for i, stage in enumerate(self.STAGES):
                stage_num = i + 1
                count = int((group["stage_num"] >= stage_num).sum())
                records.append(
                    {
                        "segmento": segment,
                        "stage": stage,
                        "count": count,
                        "pct_of_segment": round(count / total * 100, 1) if total > 0 else 0.0,
                    }
                )

        return pd.DataFrame(records)

    def get_drop_off_analysis(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Identify the biggest drop-offs in the funnel.

        Returns DataFrame sorted by drop_pct descending.
        """
        if df is None:
            df = self._load_funnel_data()

        funnel = self.get_funnel_summary(df)
        drop_offs = []
        for i in range(1, len(funnel)):
            prev = funnel.iloc[i - 1]
            curr = funnel.iloc[i]
            lost = prev["count"] - curr["count"]
            drop_offs.append(
                {
                    "transition": f"{prev['stage']} → {curr['stage']}",
                    "lost": int(lost),
                    "drop_pct": round(lost / prev["count"] * 100, 1)
                    if prev["count"] > 0
                    else 0.0,
                }
            )

        return pd.DataFrame(drop_offs).sort_values("drop_pct", ascending=False)

    def get_cohort_funnel(
        self,
        df: Optional[pd.DataFrame] = None,
        cohort_col: str = "cohort_mes",
    ) -> pd.DataFrame:
        """Funnel conversion rates broken down by signup cohort month."""
        if df is None:
            df = self._load_funnel_data()

        records = []
        for cohort, group in df.groupby(cohort_col):
            total = len(group)
            row: dict = {"cohort_mes": cohort, "n_empresas": total}
            for i, stage in enumerate(self.STAGES):
                stage_num = i + 1
                cnt = int((group["stage_num"] >= stage_num).sum())
                row[f"pct_{stage}"] = round(cnt / total * 100, 1) if total > 0 else 0.0
            records.append(row)

        return pd.DataFrame(records).sort_values("cohort_mes")

    def get_gmv_by_stage(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Average GMV per empresa at each funnel stage (converted + retained)."""
        if df is None:
            df = self._load_funnel_data()

        converted = df[df["stage_num"] >= 4]
        return (
            converted.groupby("current_stage")["gmv_total"]
            .agg(n="count", avg_gmv="mean", total_gmv="sum")
            .round(2)
            .reset_index()
        )
