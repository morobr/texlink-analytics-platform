"""
Page 01 — Platform Overview

Shows high-level platform health KPIs, monthly GMV trend, order funnel,
and a summary table of recent months.

Data source: marts_platform_kpis
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd
import streamlit as st

from src.dashboards.components.charts import bar_chart, line_chart
from src.dashboards.components.filters import date_range_filter
from src.dashboards.components.kpi_cards import kpi_row
from src.dashboards.db import db_available, run_query

st.set_page_config(page_title="Platform Overview · Texlink", page_icon="📊", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("📊 Platform Overview")
start_date, end_date = date_range_filter("po")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Visão Geral da Plataforma")
st.markdown("KPIs de saúde da plataforma Texlink por mês.")

if not db_available():
    st.warning(
        "Banco de dados não disponível. Defina DATABASE_URL e reinicie o Streamlit."
    )
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
sql = f"""
    SELECT *
    FROM marts_platform_kpis
    WHERE mes BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY mes
"""
df = run_query(sql)

if df.empty:
    st.warning("Sem dados em marts_platform_kpis para o período selecionado.")
    st.stop()

df["mes"] = pd.to_datetime(df["mes"])

# ── KPI row (latest month) ────────────────────────────────────────────────────
latest = df.iloc[-1]
prev = df.iloc[-2] if len(df) > 1 else None


def _delta(col, pct=False):
    if prev is None:
        return None
    d = latest[col] - prev[col]
    if pct:
        return d
    return d / prev[col] * 100 if prev[col] else None


kpi_row(
    [
        {
            "label": "GMV (mês atual)",
            "value": latest.get("gmv_total", 0),
            "delta": _delta("gmv_total"),
            "delta_suffix": "% MoM",
            "fmt": "R$ {:,.0f}",
        },
        {
            "label": "Take Rate",
            "value": latest.get("take_rate_pct", 0),
            "delta": _delta("take_rate_pct", pct=True),
            "delta_suffix": " pp",
            "fmt": "{:.2f}%",
        },
        {
            "label": "Match Rate",
            "value": latest.get("match_rate_pct", 0),
            "delta": _delta("match_rate_pct", pct=True),
            "delta_suffix": " pp",
            "fmt": "{:.1f}%",
        },
        {
            "label": "Empresas Ativas",
            "value": latest.get("empresas_ativas", 0),
            "delta": _delta("empresas_ativas"),
            "delta_suffix": "% MoM",
            "fmt": "{:,.0f}",
        },
        {
            "label": "Oficinas Ativas",
            "value": latest.get("oficinas_ativas", 0),
            "delta": _delta("oficinas_ativas"),
            "delta_suffix": "% MoM",
            "fmt": "{:,.0f}",
        },
    ]
)

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("GMV Mensal")
    gmv_cols = [c for c in ["gmv_total", "receita_plataforma"] if c in df.columns]
    if gmv_cols:
        fig = line_chart(df, x="mes", y_cols=gmv_cols, title="GMV e Receita (R$)", y_label="R$")
        st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("Funil de Pedidos por Mês")
    funnel_cols = [c for c in ["pedidos_publicados", "pedidos_matched", "pedidos_finalizados"] if c in df.columns]
    if funnel_cols:
        fig2 = bar_chart(df, x="mes", y=funnel_cols[0], title="Pedidos por Status")
        # Build grouped bar manually with all available cols
        import plotly.graph_objects as go
        colors = ["#0077B6", "#00B4D8", "#06D6A0"]
        fig3 = go.Figure()
        for i, col in enumerate(funnel_cols):
            fig3.add_trace(go.Bar(x=df["mes"], y=df[col], name=col, marker_color=colors[i % len(colors)]))
        fig3.update_layout(
            barmode="group",
            title="Pedidos por Status por Mês",
            height=380,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Colunas de funil não encontradas em marts_platform_kpis.")

st.markdown("---")

# ── Summary table ─────────────────────────────────────────────────────────────
st.subheader("Últimos 6 meses")
display_cols = [c for c in [
    "mes", "gmv_total", "receita_plataforma", "take_rate_pct",
    "match_rate_pct", "empresas_ativas", "oficinas_ativas",
] if c in df.columns]
last6 = df[display_cols].tail(6).copy()
last6["mes"] = last6["mes"].dt.strftime("%Y-%m")
st.dataframe(last6.set_index("mes"), use_container_width=True)
