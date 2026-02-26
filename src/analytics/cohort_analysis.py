"""
Cohort Analysis — Texlink Analytics Platform

Monthly retention cohorts and revenue cohorts for empresas.
Reads from marts_cohort_analysis view.
"""

import os
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text

load_dotenv()


class CohortAnalyzer:
    """Builds retention cohort matrices from the marts_cohort_analysis view."""

    def __init__(self, engine=None):
        if engine is None:
            db_url = os.getenv(
                "DATABASE_URL", "postgresql://texlink:password@localhost:5432/texlink"
            )
            engine = create_engine(db_url)
        self.engine = engine

    def _load_cohort_data(self) -> pd.DataFrame:
        """Load pre-aggregated cohort data from marts_cohort_analysis."""
        query = text("""
            SELECT
                cohort_mes,
                cohort_label,
                cohort_size,
                mes_n,
                n_ativos,
                retention_rate_pct,
                receita_cohort
            FROM marts_cohort_analysis
            ORDER BY cohort_mes, mes_n
        """)
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        df["cohort_mes"] = pd.to_datetime(df["cohort_mes"])
        logger.info(f"Loaded {len(df)} cohort-month records ({df['cohort_label'].nunique()} cohorts)")
        return df

    def build_retention_matrix(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Pivot cohort data into a retention matrix.

        Rows = cohort label, Columns = months since signup (mes_n).
        Values = retention_rate_pct.
        """
        if df is None:
            df = self._load_cohort_data()

        matrix = df.pivot_table(
            index="cohort_label",
            columns="mes_n",
            values="retention_rate_pct",
            aggfunc="first",
        )
        matrix.index.name = "Coorte"
        matrix.columns.name = "Mês N"
        return matrix.round(1)

    def build_revenue_matrix(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Pivot cohort data into a revenue matrix.

        Rows = cohort label, Columns = months since signup.
        Values = receita_cohort (BRL).
        """
        if df is None:
            df = self._load_cohort_data()

        matrix = df.pivot_table(
            index="cohort_label",
            columns="mes_n",
            values="receita_cohort",
            aggfunc="first",
        ).fillna(0)
        matrix.index.name = "Coorte"
        matrix.columns.name = "Mês N"
        return matrix.round(2)

    def get_average_retention_curve(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Average retention curve across all cohorts.

        Returns DataFrame: mes_n, avg_retention, median_retention, n_cohorts.
        """
        if df is None:
            df = self._load_cohort_data()

        return (
            df.groupby("mes_n")
            .agg(
                avg_retention=("retention_rate_pct", "mean"),
                median_retention=("retention_rate_pct", "median"),
                n_cohorts=("cohort_label", "count"),
            )
            .round(2)
            .reset_index()
        )

    def get_cohort_summary(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Summary per cohort: size, retention at key months, total revenue.

        Returns one row per cohort with retention_m0, m1, m3, m6.
        """
        if df is None:
            df = self._load_cohort_data()

        records = []
        for cohort_label, group in df.groupby("cohort_label"):
            def ret_at(n: int) -> Optional[float]:
                sub = group.loc[group["mes_n"] == n, "retention_rate_pct"]
                return round(float(sub.iloc[0]), 1) if len(sub) > 0 else None

            records.append(
                {
                    "cohort": cohort_label,
                    "cohort_size": int(group["cohort_size"].iloc[0]),
                    "retention_m0": ret_at(0),
                    "retention_m1": ret_at(1),
                    "retention_m3": ret_at(3),
                    "retention_m6": ret_at(6),
                    "receita_total": round(float(group["receita_cohort"].sum()), 2),
                    "receita_media_mensal": round(float(group["receita_cohort"].mean()), 2),
                    "meses_observados": int(group["mes_n"].max()),
                }
            )

        return pd.DataFrame(records).sort_values("cohort").reset_index(drop=True)

    def get_ltv_by_cohort(
        self,
        df: Optional[pd.DataFrame] = None,
        horizon_months: int = 12,
    ) -> pd.DataFrame:
        """
        Cumulative revenue per empresa up to horizon_months, by cohort.

        Args:
            horizon_months: Cap the observation window (e.g., 12 for 12-month LTV).

        Returns DataFrame: cohort_label, cohort_size, ltv_total, ltv_per_empresa.
        """
        if df is None:
            df = self._load_cohort_data()

        filtered = df[df["mes_n"] <= horizon_months]
        return (
            filtered.groupby(["cohort_label", "cohort_size"])
            .agg(ltv_total=("receita_cohort", "sum"))
            .reset_index()
            .assign(ltv_per_empresa=lambda x: (x["ltv_total"] / x["cohort_size"]).round(2))
            .sort_values("cohort_label")
            .reset_index(drop=True)
        )

    def get_best_and_worst_cohorts(
        self, df: Optional[pd.DataFrame] = None, metric: str = "retention_m3"
    ) -> dict:
        """
        Return the best and worst performing cohorts by a given metric.

        Args:
            metric: Column name from get_cohort_summary() to rank by.

        Returns dict with 'best' and 'worst' cohort labels.
        """
        summary = self.get_cohort_summary(df).dropna(subset=[metric])
        if summary.empty:
            return {"best": None, "worst": None}

        best = summary.loc[summary[metric].idxmax(), "cohort"]
        worst = summary.loc[summary[metric].idxmin(), "cohort"]
        return {"best": best, "worst": worst}
