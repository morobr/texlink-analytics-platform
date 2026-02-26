"""
Texlink Analytics — Main entry point / Landing page.

Run with:
    streamlit run src/dashboards/app.py
"""

import sys
from pathlib import Path

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src.dashboards.db import db_available, run_query

st.set_page_config(
    page_title="Texlink Analytics",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=Texlink", use_container_width=True)
    st.markdown("---")
    connected = db_available()
    if connected:
        st.success("Banco de dados: Conectado")
    else:
        st.warning("Banco de dados: Desconectado")
    st.markdown("---")
    st.markdown("**Navegação**")
    st.markdown(
        """
- 📊 Platform Overview
- 📦 Demand Analytics
- 🏭 Supply Analytics
- 🗺️ Customer Journey
- 🔗 Matching Efficiency
- 💰 Financial Analytics
        """
    )

# ── Hero ─────────────────────────────────────────────────────────────────────
st.title("🧵 Texlink Analytics Platform")
st.markdown(
    """
**Texlink** conecta **Empresas** (marcas e contratantes) a **Oficinas de Costura** (facções)
no maior marketplace têxtil do Brasil.

Este painel analítico acompanha a saúde da plataforma, a jornada do cliente,
a qualidade dos matches e a performance financeira — em tempo real.
    """
)
st.markdown("---")

# ── Top-level KPIs ────────────────────────────────────────────────────────────
st.subheader("Resumo da Plataforma")

if connected:
    kpi_sql = """
        SELECT
            SUM(gmv_total)          AS gmv_total,
            SUM(receita_plataforma) AS receita_total,
            AVG(match_rate_pct)     AS avg_match_rate,
            MAX(empresas_ativas)    AS empresas_ativas,
            MAX(oficinas_ativas)    AS oficinas_ativas
        FROM marts_platform_kpis
    """
    kpi_df = run_query(kpi_sql)

    if kpi_df.empty:
        st.warning("Sem dados em marts_platform_kpis ainda.")
    else:
        row = kpi_df.iloc[0]
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("GMV Total", f"R$ {row['gmv_total']:,.0f}")
        with col2:
            st.metric("Receita Plataforma", f"R$ {row['receita_total']:,.0f}")
        with col3:
            st.metric("Match Rate", f"{row['avg_match_rate']:.1f}%")
        with col4:
            st.metric("Empresas Ativas", f"{int(row['empresas_ativas']):,}")
        with col5:
            st.metric("Oficinas Ativas", f"{int(row['oficinas_ativas']):,}")
else:
    st.warning(
        "Conecte ao banco de dados para ver os KPIs. "
        "Defina a variável de ambiente **DATABASE_URL** e reinicie."
    )
    col1, col2, col3, col4, col5 = st.columns(5)
    for col, label in zip(
        [col1, col2, col3, col4, col5],
        ["GMV Total", "Receita", "Match Rate", "Empresas", "Oficinas"],
    ):
        with col:
            st.metric(label, "—")

st.markdown("---")

# ── About section ─────────────────────────────────────────────────────────────
col_l, col_r = st.columns([2, 1])
with col_l:
    st.subheader("Sobre este projeto")
    st.markdown(
        """
### Stack Técnica
| Camada | Tecnologia |
|---|---|
| Banco de dados | PostgreSQL 16 (Railway) |
| Modelagem | SQL (Views dbt-style) |
| Analytics / ML | Python, PyMC, scikit-learn |
| Dashboards | Streamlit + Plotly + Altair |
| Deploy | Railway.com + GitHub Actions |

### Arquitetura de dados
```
Fontes → Staging → Intermediate → Marts → Dashboards
```
- **14 tabelas** de origem (pedidos, propostas, pagamentos…)
- **11 views** de staging
- **6 views** intermediárias
- **8 marts** analíticos
        """
    )

with col_r:
    st.subheader("Métricas-chave")
    st.markdown(
        """
- **GMV** — Valor bruto de pedidos
- **Take Rate** — Receita / GMV
- **Match Rate** — Pedidos matchados
- **Liquidez** — Pedidos c/ ≥1 proposta
- **CLV** — Lifetime Value da empresa
- **Fill Rate** — Capacidade utilizada
- **Win Rate** — Taxa de sucesso da oficina
- **Quality Score** — Score composto (0–10)
        """
    )

st.markdown("---")
st.caption("Texlink Analytics Platform · Powered by Claude Code · 2026")
