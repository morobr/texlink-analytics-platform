"""
Page 05 — Matching Efficiency

Shows match quality KPIs, geographic breakdown, supply-demand gap table,
and GMV by empresa state.

Data sources: marts_match_quality, marts_geographic_analysis
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit as st

from src.dashboards.components.charts import bar_chart
from src.dashboards.components.kpi_cards import kpi_row
from src.dashboards.db import db_available, run_query

st.set_page_config(page_title="Matching Efficiency · Texlink", page_icon="🔗", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🔗 Matching Efficiency")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🔗 Eficiência de Matching")
st.markdown("Qualidade dos matches Empresa ↔ Oficina e gaps de oferta/demanda.")

if not db_available():
    st.warning("Banco de dados não disponível. Defina DATABASE_URL e reinicie.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
mq_df = run_query("SELECT * FROM marts_match_quality")
geo_df = run_query("SELECT * FROM marts_geographic_analysis")

if mq_df.empty and geo_df.empty:
    st.warning("Sem dados em marts_match_quality / marts_geographic_analysis.")
    st.stop()

# ── KPI row ───────────────────────────────────────────────────────────────────
def _safe_mean(df, col):
    return float(df[col].mean()) if not df.empty and col in df.columns else 0.0

def _safe_pct(df, col, val):
    if df.empty or col not in df.columns:
        return 0.0
    return float((df[col] == val).mean() * 100)

match_rate = _safe_mean(mq_df, "pct_finalizado")
avg_quality = _safe_mean(mq_df, "avg_match_quality")
repeat_pair_pct = float(mq_df["pct_repeat"].mean()) if not mq_df.empty and "pct_repeat" in mq_df.columns else 0.0
interestadual_pct = _safe_pct(mq_df, "tipo_match_geografico", "interestadual")

kpi_row(
    [
        {"label": "Match Rate %", "value": match_rate, "fmt": "{:.1f}%"},
        {"label": "Score Médio de Match", "value": avg_quality, "fmt": "{:.2f}"},
        {"label": "Pares Repetidos %", "value": repeat_pair_pct, "fmt": "{:.1f}%"},
        {"label": "Interestadual %", "value": interestadual_pct, "fmt": "{:.1f}%"},
    ]
)

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Matches por Tipo Geográfico")
    if not mq_df.empty and "tipo_match_geografico" in mq_df.columns:
        geo_counts = mq_df.groupby("tipo_match_geografico")["total_matches"].sum().reset_index()
        geo_counts.columns = ["tipo_match_geografico", "count"]
        fig = bar_chart(geo_counts, x="tipo_match_geografico", y="count", title="Distribuição por Tipo Geo")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dados de tipo geográfico não encontrados.")

with col_r:
    st.subheader("GMV Matched por Estado da Empresa")
    gmv_col = None
    estado_col = None
    for df_ in [mq_df, geo_df]:
        if df_.empty:
            continue
        for ec in ["empresa_estado", "estado_empresa", "estado"]:
            if ec in df_.columns:
                estado_col = ec
                break
        for gc in ["gmv_matched", "gmv_total"]:
            if gc in df_.columns:
                gmv_col = gc
                break
        if estado_col and gmv_col:
            agg = df_.groupby(estado_col)[gmv_col].sum().reset_index().sort_values(gmv_col, ascending=True)
            fig2 = bar_chart(agg, x=gmv_col, y=estado_col, title=f"{gmv_col} por Estado", orientation="h")
            st.plotly_chart(fig2, use_container_width=True)
            break
    if not (estado_col and gmv_col):
        st.info("Dados de GMV por estado não encontrados.")

st.markdown("---")

# ── Supply-demand gap table ───────────────────────────────────────────────────
st.subheader("Gap Oferta-Demanda por Estado")
if not geo_df.empty:
    gap_cols = [c for c in [
        "estado", "n_empresas", "n_oficinas", "gap_score",
        "demanda_total", "oferta_total",
    ] if c in geo_df.columns]
    if gap_cols:
        sort_col = "gap_score" if "gap_score" in gap_cols else gap_cols[-1]
        gap_table = geo_df[gap_cols].sort_values(sort_col, ascending=False)
        st.dataframe(gap_table, use_container_width=True, hide_index=True)
    else:
        st.dataframe(geo_df.head(30), use_container_width=True, hide_index=True)
else:
    st.info("Sem dados de análise geográfica.")
