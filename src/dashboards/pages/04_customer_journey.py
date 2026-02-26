"""
Page 04 — Customer Journey

Funnel analysis (signup → retained), stage transition times,
cohort retention heatmap, and average retention curve.

Data sources: int_funnel_stages (via CustomerJourneyAnalyzer),
              marts_cohort_analysis (via CohortAnalyzer)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit as st

from src.dashboards.components.charts import bar_chart, cohort_heatmap, funnel_chart, line_chart
from src.dashboards.components.kpi_cards import kpi_row
from src.dashboards.db import db_available, get_engine

st.set_page_config(page_title="Customer Journey · Texlink", page_icon="🗺️", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🗺️ Customer Journey")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🗺️ Jornada do Cliente — Empresas")
st.markdown("Funil de conversão completo e análise de coorte de retenção.")

if not db_available():
    st.warning("Banco de dados não disponível. Defina DATABASE_URL e reinicie.")
    st.stop()

# ── Load via analytics modules ────────────────────────────────────────────────
engine = get_engine()

try:
    from src.analytics.cohort_analysis import CohortAnalyzer
    from src.analytics.customer_journey import CustomerJourneyAnalyzer

    journey = CustomerJourneyAnalyzer(engine=engine)
    cohort = CohortAnalyzer(engine=engine)

    funnel_df = journey.get_funnel_summary()
    time_df = journey.get_time_to_convert()
    retention_matrix = cohort.build_retention_matrix()
    avg_curve = cohort.get_average_retention_curve()
    data_ok = True
except Exception as exc:
    st.error(f"Erro ao carregar dados de jornada: {exc}")
    data_ok = False

if not data_ok:
    st.stop()

# ── KPI row ───────────────────────────────────────────────────────────────────
def _rate(stage):
    row = funnel_df[funnel_df["stage"] == stage]
    return float(row["pct_of_top"].iloc[0]) if not row.empty else 0.0


kpi_row(
    [
        {"label": "Taxa de Ativação", "value": _rate("activated"), "fmt": "{:.1f}%"},
        {"label": "Taxa de Match", "value": _rate("matched"), "fmt": "{:.1f}%"},
        {"label": "Taxa de Conversão", "value": _rate("converted"), "fmt": "{:.1f}%"},
        {"label": "Taxa de Retenção", "value": _rate("retained"), "fmt": "{:.1f}%"},
    ]
)

st.markdown("---")

# ── Funnel chart ──────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Funil de Conversão")
    fig = funnel_chart(
        stages=funnel_df["stage_label"].tolist(),
        counts=funnel_df["count"].tolist(),
        title="Signup → Retenção",
    )
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("Tempo Mediano por Etapa (dias)")
    if not time_df.empty and "transicao" in time_df.columns:
        fig2 = bar_chart(
            time_df.dropna(subset=["mediana_dias"]),
            x="mediana_dias",
            y="transicao",
            title="Mediana de Dias por Transição",
            orientation="h",
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem dados de tempo de conversão.")

st.markdown("---")

# ── Cohort heatmap ────────────────────────────────────────────────────────────
st.subheader("Heatmap de Retenção por Cohort")
if retention_matrix is not None and not retention_matrix.empty:
    chart = cohort_heatmap(retention_matrix, title="Retenção Mensal por Cohort de Cadastro")
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("Sem dados de cohort disponíveis.")

st.markdown("---")

# ── Average retention curve ───────────────────────────────────────────────────
st.subheader("Curva Média de Retenção")
if avg_curve is not None and not avg_curve.empty:
    mes_col = avg_curve.columns[0] if "mes_n" not in avg_curve.columns else "mes_n"
    ret_col = "avg_retention" if "avg_retention" in avg_curve.columns else avg_curve.columns[-1]
    fig3 = line_chart(
        avg_curve,
        x=mes_col,
        y_cols=[ret_col],
        title="Retenção Média (% de empresas ativas por mês desde cadastro)",
        y_label="Retenção %",
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Sem dados de curva de retenção.")
