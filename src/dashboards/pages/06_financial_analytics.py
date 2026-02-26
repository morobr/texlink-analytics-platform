"""
Page 06 — Financial Analytics

GMV, revenue, take rate, payment mix, and MoM growth.

Data source: marts_revenue_analytics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd
import streamlit as st

from src.dashboards.components.charts import bar_chart, donut_chart, dual_axis_line_chart
from src.dashboards.components.filters import date_range_filter
from src.dashboards.components.kpi_cards import kpi_row
from src.dashboards.db import db_available, run_query

st.set_page_config(page_title="Financial Analytics · Texlink", page_icon="💰", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("💰 Financial Analytics")
start_date, end_date = date_range_filter("fin")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("💰 Analytics Financeiro")
st.markdown("GMV, receita, take rate e mix de meios de pagamento.")

if not db_available():
    st.warning("Banco de dados não disponível. Defina DATABASE_URL e reinicie.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
sql = f"""
    SELECT *
    FROM marts_revenue_analytics
    WHERE mes BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY mes
"""
df = run_query(sql)

if df.empty:
    st.warning("Sem dados em marts_revenue_analytics para o período selecionado.")
    st.stop()

df["mes"] = pd.to_datetime(df["mes"])

# ── KPI row ───────────────────────────────────────────────────────────────────
total_gmv = df["gmv"].sum() if "gmv" in df.columns else 0
total_receita = df["receita_plataforma"].sum() if "receita_plataforma" in df.columns else 0
avg_take_rate = df["take_rate_real_pct"].mean() if "take_rate_real_pct" in df.columns else 0
avg_ticket = df["ticket_medio"].mean() if "ticket_medio" in df.columns else 0

kpi_row(
    [
        {"label": "GMV Total (período)", "value": total_gmv, "fmt": "R$ {:,.0f}"},
        {"label": "Receita Total", "value": total_receita, "fmt": "R$ {:,.0f}"},
        {"label": "Take Rate Médio", "value": avg_take_rate, "fmt": "{:.2f}%"},
        {"label": "Ticket Médio", "value": avg_ticket, "fmt": "R$ {:,.0f}"},
    ]
)

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("GMV e Receita por Mês")
    gmv_col = "gmv" if "gmv" in df.columns else None
    rev_col = "receita_plataforma" if "receita_plataforma" in df.columns else None
    if gmv_col and rev_col:
        fig = dual_axis_line_chart(
            df, x="mes", y1=gmv_col, y2=rev_col,
            y1_label="GMV (R$)", y2_label="Receita (R$)",
            title="GMV vs Receita",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Colunas GMV/Receita não encontradas.")

with col_r:
    st.subheader("Crescimento MoM do GMV (%)")
    if "gmv" in df.columns:
        df_growth = df[["mes", "gmv"]].copy()
        df_growth["gmv_mom_pct"] = df_growth["gmv"].pct_change() * 100
        df_growth = df_growth.dropna(subset=["gmv_mom_pct"])
        if not df_growth.empty:
            fig2 = bar_chart(
                df_growth, x="mes", y="gmv_mom_pct",
                title="Crescimento MoM do GMV (%)",
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Dados insuficientes para cálculo de MoM.")
    else:
        st.info("Coluna gmv não encontrada.")

st.markdown("---")

# ── Payment mix donut ─────────────────────────────────────────────────────────
col_pay, col_table = st.columns([1, 2])

with col_pay:
    st.subheader("Mix de Pagamentos")
    pay_cols = [c for c in df.columns if c.startswith("pct_") or "pagamento" in c.lower() or c in ["pix", "boleto", "transferencia"]]

    # Try to find payment split columns (pct_pix, pct_boleto, pct_transferencia)
    payment_map = {
        "PIX": next((c for c in df.columns if "pix" in c.lower()), None),
        "Boleto": next((c for c in df.columns if "boleto" in c.lower()), None),
        "Transferência": next((c for c in df.columns if "transfer" in c.lower()), None),
    }
    valid_pay = {k: v for k, v in payment_map.items() if v is not None}

    if valid_pay:
        pay_df = pd.DataFrame(
            [{"metodo": k, "valor": df[v].mean()} for k, v in valid_pay.items()]
        )
        fig3 = donut_chart(pay_df, names="metodo", values="valor", title="Mix de Pagamentos")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Dados de mix de pagamento não encontrados nas colunas do mart.")

with col_table:
    st.subheader("Breakdown Mensal")
    display_cols = [c for c in [
        "mes", "gmv", "receita_plataforma", "take_rate_real_pct",
        "ticket_medio", "n_pagamentos",
    ] if c in df.columns]
    table = df[display_cols].copy()
    table["mes"] = table["mes"].dt.strftime("%Y-%m")
    st.dataframe(table.set_index("mes"), use_container_width=True)
