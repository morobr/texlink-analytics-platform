"""
Page 03 — Supply Analytics (Oficinas)

Shows tier distribution, score by estado, and a filterable ranked table.

Data sources: marts_oficina_scoring, marts_geographic_analysis
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd
import streamlit as st

from src.dashboards.components.charts import bar_chart, donut_chart
from src.dashboards.components.filters import estado_filter, score_range_filter, tier_filter
from src.dashboards.components.kpi_cards import kpi_row
from src.dashboards.db import db_available, run_query

st.set_page_config(page_title="Supply Analytics · Texlink", page_icon="🏭", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🏭 Supply Analytics")
selected_tiers = tier_filter()
score_min, score_max = score_range_filter()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏭 Analytics de Oferta — Oficinas de Costura")
st.markdown("Score de qualidade, distribuição por tier e cobertura geográfica.")

if not db_available():
    st.warning("Banco de dados não disponível. Defina DATABASE_URL e reinicie.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
sql = "SELECT * FROM marts_oficina_scoring ORDER BY score_composto DESC NULLS LAST"
df = run_query(sql)

if df.empty:
    st.warning("Sem dados em marts_oficina_scoring.")
    st.stop()

# Apply sidebar filters
if selected_tiers and "tier" in df.columns:
    df = df[df["tier"].isin(selected_tiers)]
if "score_composto" in df.columns:
    df = df[df["score_composto"].between(score_min, score_max)]

estados_available = df["estado"].dropna().unique().tolist() if "estado" in df.columns else []
selected_estados = estado_filter(estados_available, key="estado_supply")
if selected_estados and "estado" in df.columns:
    df = df[df["estado"].isin(selected_estados)]

# ── KPI row ───────────────────────────────────────────────────────────────────
total_oficinas = len(df)
avg_score = df["score_composto"].mean() if "score_composto" in df.columns else 0
elite_prem_pct = (
    df["tier"].isin(["elite", "premium"]).mean() * 100
    if "tier" in df.columns else 0
)
abvtex_pct = (
    (df["tem_abvtex"] == True).mean() * 100  # noqa: E712
    if "tem_abvtex" in df.columns else 0
)

kpi_row(
    [
        {"label": "Total Oficinas", "value": total_oficinas, "fmt": "{:,.0f}"},
        {"label": "Score Médio", "value": avg_score, "fmt": "{:.2f}"},
        {"label": "Elite + Premium %", "value": elite_prem_pct, "fmt": "{:.1f}%"},
        {"label": "Certificadas ABVTEX %", "value": abvtex_pct, "fmt": "{:.1f}%"},
    ]
)

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Distribuição por Tier")
    if "tier" in df.columns:
        tier_counts = df["tier"].value_counts().reset_index()
        tier_counts.columns = ["tier", "count"]
        tier_order = ["elite", "premium", "standard", "basico"]
        tier_counts["tier"] = pd.Categorical(tier_counts["tier"], categories=tier_order, ordered=True)
        tier_counts = tier_counts.sort_values("tier")
        fig = donut_chart(tier_counts, names="tier", values="count", title="Tiers de Oficinas")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Coluna 'tier' não encontrada.")

with col_r:
    st.subheader("Oficinas e Score por Estado")
    if "estado" in df.columns and "score_composto" in df.columns:
        estado_agg = (
            df.groupby("estado")
            .agg(n_oficinas=("estado", "count"), avg_score=("score_composto", "mean"))
            .reset_index()
            .sort_values("avg_score", ascending=True)
        )
        fig2 = bar_chart(
            estado_agg, x="avg_score", y="estado",
            title="Score Médio por Estado", orientation="h",
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Colunas 'estado' / 'score_composto' não encontradas.")

st.markdown("---")

# ── Ranked table ──────────────────────────────────────────────────────────────
st.subheader("Ranking de Oficinas")
display_cols = [c for c in [
    "oficina_id", "estado", "tier", "score_composto",
    "dim_qualidade", "dim_pontualidade", "dim_comunicacao",
    "dim_experiencia", "dim_certificacoes", "dim_velocidade",
    "tem_abvtex",
] if c in df.columns]
st.dataframe(df[display_cols].head(100), use_container_width=True, hide_index=True)
