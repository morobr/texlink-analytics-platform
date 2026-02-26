"""
Customer Lifetime Value Model — Texlink Analytics Platform

BG/NBD (Buy-Till-They-Die) + Gamma-Gamma model for empresa CLV prediction.
Uses the `lifetimes` library for BG/NBD and Gamma-Gamma fitting.

Reference: Fader, Hardie, Lee (2005) — "Counting Your Customers: Who Are They
           and What Will They Do Next?"
"""

import os
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text

try:
    from lifetimes import BetaGeoFitter, GammaGammaFitter
    from lifetimes.utils import summary_data_from_transaction_data as summary_data_from_transaction_dataframe

    HAS_LIFETIMES = True
except ImportError:  # pragma: no cover
    HAS_LIFETIMES = False
    logger.warning("lifetimes not installed. Run: pip install lifetimes")

load_dotenv()


class CLVModel:
    """
    Customer Lifetime Value model for Texlink empresas.

    Workflow:
        model = CLVModel()
        model.fit()
        clv_df = model.predict_clv(months=12)

    Requires the `lifetimes` package (included in requirements.txt).
    """

    def __init__(self, engine=None, penalizer_coef: float = 0.001):
        if engine is None:
            db_url = os.getenv(
                "DATABASE_URL", "postgresql://texlink:password@localhost:5432/texlink"
            )
            engine = create_engine(db_url)
        self.engine = engine
        self.penalizer_coef = penalizer_coef
        self.bgf: Optional["BetaGeoFitter"] = None
        self.ggf: Optional["GammaGammaFitter"] = None
        self._rfm_df: Optional[pd.DataFrame] = None

    # ──────────────────────────────────────────────
    # Data loading
    # ──────────────────────────────────────────────

    def _load_transaction_data(self) -> pd.DataFrame:
        """Load one row per completed order from stg_pedidos."""
        query = text("""
            SELECT
                empresa_id,
                dt_criacao::date   AS order_date,
                valor_final
            FROM stg_pedidos
            WHERE foi_finalizado
              AND valor_final > 0
            ORDER BY empresa_id, dt_criacao
        """)
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, parse_dates=["order_date"])
        logger.info(f"Loaded {len(df)} completed orders for {df['empresa_id'].nunique()} empresas")
        return df

    def build_rfm_summary(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Build the RFM summary table required by the lifetimes library.

        Columns produced:
            frequency       — number of *repeat* purchases (total - 1)
            recency         — days between first and last purchase
            T               — days from first purchase to observation end
            monetary_value  — average order value (all purchases)

        Args:
            df: Optional raw transaction DataFrame (empresa_id, order_date, valor_final).
                If None, loads from DB.

        Returns:
            DataFrame indexed by empresa_id.
        """
        if not HAS_LIFETIMES:
            raise ImportError("lifetimes package is required: pip install lifetimes")

        if df is None:
            df = self._load_transaction_data()

        observation_end = df["order_date"].max()
        rfm = summary_data_from_transaction_dataframe(
            df,
            customer_id_col="empresa_id",
            datetime_col="order_date",
            monetary_value_col="valor_final",
            observation_period_end=observation_end,
            freq="D",
        )
        self._rfm_df = rfm
        logger.info(
            f"RFM summary: {len(rfm)} empresas, "
            f"{(rfm['frequency'] > 0).sum()} with repeat purchases"
        )
        return rfm

    # ──────────────────────────────────────────────
    # Model fitting
    # ──────────────────────────────────────────────

    def fit(self, df: Optional[pd.DataFrame] = None) -> "CLVModel":
        """
        Fit BG/NBD + Gamma-Gamma models.

        Args:
            df: Optional pre-built RFM summary. If None, loads from DB.

        Returns:
            self (for method chaining).
        """
        if not HAS_LIFETIMES:
            raise ImportError("lifetimes package is required: pip install lifetimes")

        rfm = df if df is not None else self.build_rfm_summary()

        # --- BG/NBD ---
        logger.info(f"Fitting BG/NBD on {len(rfm)} empresas …")
        self.bgf = BetaGeoFitter(penalizer_coef=self.penalizer_coef)
        self.bgf.fit(rfm["frequency"], rfm["recency"], rfm["T"])
        logger.info(
            f"BG/NBD params: r={self.bgf.params_['r']:.4f}, "
            f"alpha={self.bgf.params_['alpha']:.4f}, "
            f"a={self.bgf.params_['a']:.4f}, "
            f"b={self.bgf.params_['b']:.4f}"
        )

        # --- Gamma-Gamma (repeat buyers only) ---
        gg_df = rfm[rfm["frequency"] > 0]
        logger.info(f"Fitting Gamma-Gamma on {len(gg_df)} repeat-purchase empresas …")
        self.ggf = GammaGammaFitter(penalizer_coef=self.penalizer_coef)
        self.ggf.fit(gg_df["frequency"], gg_df["monetary_value"])
        logger.info(
            f"Gamma-Gamma params: p={self.ggf.params_['p']:.4f}, "
            f"q={self.ggf.params_['q']:.4f}, "
            f"v={self.ggf.params_['v']:.4f}"
        )

        return self

    # ──────────────────────────────────────────────
    # Prediction
    # ──────────────────────────────────────────────

    def predict_clv(
        self,
        months: int = 12,
        discount_rate: float = 0.01,
        rfm_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Predict CLV for each empresa over the next N months.

        Args:
            months:        Prediction horizon in months.
            discount_rate: Monthly discount rate for NPV calculation.
            rfm_df:        Optional RFM DataFrame; uses cached if None.

        Returns:
            DataFrame sorted by predicted CLV descending, with columns:
                empresa_id, frequency, recency_days, age_days,
                avg_order_value, expected_purchases_{n}m, clv_{n}m_predicted.
        """
        if self.bgf is None or self.ggf is None:
            raise RuntimeError("Model not fitted — call .fit() first")

        df = rfm_df if rfm_df is not None else self._rfm_df
        if df is None:
            raise RuntimeError("No RFM data — call fit() or pass rfm_df")

        expected_purchases = self.bgf.predict(
            months * 30,  # days in horizon
            df["frequency"],
            df["recency"],
            df["T"],
        )

        clv = self.ggf.customer_lifetime_value(
            self.bgf,
            df["frequency"],
            df["recency"],
            df["T"],
            df["monetary_value"].fillna(0),
            time=months,
            discount_rate=discount_rate,
            freq="D",
        )

        prob_alive = self.bgf.conditional_probability_alive(
            df["frequency"], df["recency"], df["T"]
        )

        result = pd.DataFrame(
            {
                "empresa_id": df.index,
                "frequency": df["frequency"].values,
                "recency_days": df["recency"].values,
                "age_days": df["T"].values,
                "avg_order_value": df["monetary_value"].fillna(0).round(2).values,
                f"expected_purchases_{months}m": np.asarray(expected_purchases).round(3),
                f"clv_{months}m_predicted": np.asarray(clv).round(2),
                "prob_alive": np.asarray(prob_alive).round(4),
            }
        ).sort_values(f"clv_{months}m_predicted", ascending=False)

        logger.info(
            f"CLV prediction ({months}m): median={result[f'clv_{months}m_predicted'].median():.2f}, "
            f"top-10 avg={result.head(10)[f'clv_{months}m_predicted'].mean():.2f}"
        )
        return result.reset_index(drop=True)

    def get_expected_purchases(
        self,
        t_days: int = 30,
        rfm_df: Optional[pd.DataFrame] = None,
    ) -> pd.Series:
        """Expected number of purchases in the next t_days for each empresa."""
        if self.bgf is None:
            raise RuntimeError("Model not fitted — call .fit() first")
        df = rfm_df if rfm_df is not None else self._rfm_df
        return self.bgf.predict(t_days, df["frequency"], df["recency"], df["T"])

    def probability_alive(self, rfm_df: Optional[pd.DataFrame] = None) -> pd.Series:
        """Probability that each empresa is still an active buyer."""
        if self.bgf is None:
            raise RuntimeError("Model not fitted — call .fit() first")
        df = rfm_df if rfm_df is not None else self._rfm_df
        result = self.bgf.conditional_probability_alive(
            df["frequency"], df["recency"], df["T"]
        )
        return pd.Series(np.asarray(result), index=df.index, name="prob_alive")

    def segment_by_clv(
        self,
        clv_df: Optional[pd.DataFrame] = None,
        months: int = 12,
        n_segments: int = 4,
    ) -> pd.DataFrame:
        """
        Add a CLV segment label (quartile-based) to the CLV DataFrame.

        Segments: 'high_value', 'mid_high', 'mid_low', 'low_value'
        """
        if clv_df is None:
            clv_df = self.predict_clv(months=months)

        col = f"clv_{months}m_predicted"
        labels = ["low_value", "mid_low", "mid_high", "high_value"]
        clv_df = clv_df.copy()
        clv_df["clv_segment"] = pd.qcut(
            clv_df[col],
            q=n_segments,
            labels=labels[: n_segments],
            duplicates="drop",
        )
        return clv_df

    @property
    def is_fitted(self) -> bool:
        return self.bgf is not None and self.ggf is not None
