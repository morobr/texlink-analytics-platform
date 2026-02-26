"""
Page 02 — Demand Analytics (Empresas / CLV)

Shows RFM segmentation, CLV distribution, scatter of recency vs frequency,
and a filterable top-empresas table.

Data source: marts_empresa_clv
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit as st

from src.dashboards.components.charts import bar_chart, scatter_chart
from src.dashboards.components.filters import segment_filter
from src.dashboards.components.kpi_cards import kpi_row
from src.dashboards.db import db_available, run_query

st.set_page_config(page_title="Demand Analytics · Texlink", page_icon="📦", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("📦 Demand Analytics")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📦 Analytics de Demanda — Empresas")
st.markdown("Segmentação RFM, CLV e comportamento das empresas na plataforma.")

if not db_available():
    st.warning("Banco de dados não disponível. Defina DATABASE_URL e reinicie.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
sql = "SELECT * FROM marts_empresa_clv ORDER BY clv_12m_estimado DESC NULLS LAST"
df = run_query(sql)

if df.empty:
    st.warning("Sem dados em marts_empresa_clv.")
    st.stop()

# Sidebar filters
segments_available = df["segmento"].dropna().unique().tolist() if "segmento" in df.columns else []
selected_segments = segment_filter(segments_available, key="seg_demand")
if selected_segments:
    df = df[df["segmento"].isin(selected_segments)]

# ── KPI row ───────────────────────────────────────────────────────────────────
total_empresas = len(df)
median_clv = df["clv_12m_estimado"].median() if "clv_12m_estimado" in df.columns else 0
champions_pct = (
    (df["rfm_segment"] == "campeoes").mean() * 100
    if "rfm_segment" in df.columns else 0
)
activation_rate = (
    (df["frequencia"] > 0).mean() * 100
    if "frequencia" in df.columns else 0
)

kpi_row(
    [
        {"label": "Total Empresas", "value": total_empresas, "fmt": "{:,.0f}"},
        {"label": "CLV Mediano (12m)", "value": median_clv, "fmt": "R$ {:,.0f}"},
        {"label": "Campeões %", "value": champions_pct, "fmt": "{:.1f}%"},
        {"label": "Taxa de Ativação", "value": activation_rate, "fmt": "{:.1f}%"},
    ]
)

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Empresas por Segmento RFM")
    if "rfm_segment" in df.columns:
        seg_counts = df["rfm_segment"].value_counts().reset_index()
        seg_counts.columns = ["rfm_segment", "count"]
        fig = bar_chart(seg_counts, x="rfm_segment", y="count", title="Distribuição RFM")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Coluna rfm_segment não encontrada.")

with col_r:
    st.subheader("Recência vs Frequência")
    x_col = "recency_dias" if "recency_dias" in df.columns else None
    y_col = "frequencia" if "frequencia" in df.columns else None
    size_col = "gasto_total" if "gasto_total" in df.columns else None
    color_col = "rfm_segment" if "rfm_segment" in df.columns else None

    if x_col and y_col:
        sample = df.head(500)  # cap for performance
        fig2 = scatter_chart(
            sample,
            x=x_col,
            y=y_col,
            color=color_col,
            size=size_col,
            title="Recência vs Frequência (bolha = gasto total)",
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Colunas de recência/frequência não encontradas.")

st.markdown("---")

# ── Top empresas table ────────────────────────────────────────────────────────
st.subheader("Top 50 Empresas por CLV")
display_cols = [c for c in [
    "empresa_id", "segmento", "porte", "estado",
    "rfm_segment", "clv_12m_estimado", "gasto_total", "frequencia", "recency_dias",
] if c in df.columns]
top50 = df[display_cols].head(50)
st.dataframe(top50, use_container_width=True, hide_index=True)
