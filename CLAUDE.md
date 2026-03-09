# CLAUDE.md — Development Guide

> This file serves as the project knowledge base for AI-assisted development tooling (Claude Code).
> It documents architecture, conventions, and domain context used during development.
> See [docs/architecture.md](docs/architecture.md) for the technical architecture documentation.

## Project Purpose
This is a **showcase analytics engineering project** for Texlink (texlink.com.br), a Brazilian textile marketplace startup that connects **Empresas (brands/contractors)** to **Oficinas de Costura (sewing workshops/service providers)**.

The project demonstrates end-to-end analytics engineering capabilities: database design, data modeling, customer journey analytics, and interactive dashboards — all deployed on Railway.com with PostgreSQL.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    TEXLINK ANALYTICS                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Railway   │───▶│  PostgreSQL   │───▶│  Analytics   │  │
│  │ Deploy    │    │  (Source DB)  │    │  Layer       │  │
│  └──────────┘    └──────────────┘    └──────────────┘  │
│                         │                    │          │
│                         ▼                    ▼          │
│                  ┌──────────────┐    ┌──────────────┐  │
│                  │  dbt-style   │    │  Streamlit    │  │
│                  │  Models      │    │  Dashboards   │  │
│                  │  (SQL + Py)  │    │              │  │
│                  └──────────────┘    └──────────────┘  │
│                         │                    │          │
│                         ▼                    ▼          │
│                  ┌──────────────────────────────────┐  │
│                  │  Marts: Platform KPIs, Customer  │  │
│                  │  Journey, Funnel, Cohort, CLV    │  │
│                  └──────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🗃️ Database Schema (PostgreSQL on Railway)

### Source Tables (Transactional)
| Table | Description |
|---|---|
| `empresas` | Brand/contractor companies registered on the platform |
| `oficinas` | Sewing workshops (service providers) |
| `usuarios` | Platform users (linked to empresas or oficinas) |
| `pedidos` | Production orders placed by empresas |
| `pedido_items` | Line items within each order |
| `propostas` | Proposals/bids from oficinas on pedidos |
| `producao` | Production tracking per order |
| `avaliacoes` | Quality ratings and reviews |
| `certificacoes` | Workshop certifications (ABVTEX, NBCU, Disney, etc.) |
| `pagamentos` | Payment transactions |
| `mensagens` | In-platform messaging between parties |
| `eventos_plataforma` | Platform event log (clickstream / activity tracking) |
| `categorias_produto` | Product categories in textile industry |
| `notificacoes` | System notifications sent to users |

### Analytics Models (Layered)

#### Staging (`stg_`)
Clean, typed, renamed source tables. 1:1 with source.

#### Intermediate (`int_`)
Business logic joins and transformations:
- `int_pedidos_enriched` — Orders with empresa + oficina details
- `int_oficina_performance` — Workshop metrics aggregation
- `int_empresa_activity` — Brand engagement metrics
- `int_funnel_stages` — Customer journey stage mapping

#### Marts (`marts_`)
Final analytical tables:
- `marts_platform_kpis` — Daily/weekly/monthly platform metrics
- `marts_customer_journey` — Full funnel from signup → first order → repeat
- `marts_cohort_analysis` — Retention cohorts by signup month
- `marts_oficina_scoring` — Workshop quality scoring system
- `marts_empresa_clv` — Customer Lifetime Value for brands
- `marts_match_quality` — Empresa↔Oficina match effectiveness
- `marts_revenue_analytics` — Revenue, GMV, take-rate analysis
- `marts_geographic_analysis` — Regional supply/demand heatmaps

---

## 🔑 Key Business Metrics

### Platform Health
- **GMV** (Gross Merchandise Value): Total value of orders
- **Take Rate**: Platform revenue / GMV
- **Liquidity**: % of orders that receive at least 1 proposal
- **Time-to-Match**: Hours from order creation to accepted proposal
- **Active Rate**: % of registered users active in last 30 days

### Demand Side (Empresas)
- **Activation Rate**: % of signups that place first order
- **Repeat Rate**: % of empresas with 2+ orders
- **CLV**: Customer Lifetime Value
- **Order Frequency**: Orders per empresa per month
- **Avg Order Value (AOV)**

### Supply Side (Oficinas)
- **Fill Rate**: % of available capacity utilized
- **Win Rate**: Proposals accepted / Proposals sent
- **Quality Score**: Composite score from ratings + certifications + on-time delivery
- **Response Time**: Avg time to submit proposal after order published
- **Churn Risk**: Probability of becoming inactive

### Matching Efficiency
- **Match Rate**: % of orders successfully matched
- **Match Quality Score**: Post-delivery satisfaction for matched pairs
- **Geographic Coverage**: Supply coverage by region
- **Category Coverage**: Oficina capabilities vs demand categories

---

## 📁 Project Structure
```
texlink-analytics/
├── CLAUDE.md                  # This file — AI development guide
├── README.md                  # Project showcase documentation
├── PROGRESS.md                # Task tracking and progress log
├── requirements.txt           # Python dependencies
├── pyproject.toml             # Project metadata
├── .env.example               # Environment variables template
├── railway.toml               # Railway deployment config
├── docker-compose.yml         # Local development with PostgreSQL
├── docs/
│   ├── data_dictionary.md     # Full schema documentation
│   ├── business_glossary.md   # Business terms definitions
│   └── architecture.md        # Technical architecture details
├── src/
│   ├── database/
│   │   ├── schema.sql         # DDL for all tables
│   │   ├── indexes.sql        # Performance indexes
│   │   └── functions.sql      # PostgreSQL functions/triggers
│   ├── seeds/
│   │   ├── seed_generator.py  # Faker-based dummy data generator
│   │   ├── seed_config.yaml   # Configuration for data volumes
│   │   └── seed_loader.py     # Load seeds into PostgreSQL
│   ├── models/
│   │   ├── staging/           # stg_ models (cleaning layer)
│   │   ├── intermediate/      # int_ models (business logic)
│   │   └── marts/             # marts_ models (analytics-ready)
│   ├── analytics/
│   │   ├── customer_journey.py    # Journey/funnel analysis
│   │   ├── cohort_analysis.py     # Retention cohorts
│   │   ├── clv_model.py           # CLV estimation (Bayesian)
│   │   ├── scoring_model.py       # Oficina quality scoring
│   │   └── match_optimization.py  # Supply-demand matching
│   └── dashboards/
│       ├── app.py                 # Streamlit main app
│       ├── pages/
│       │   ├── 01_platform_overview.py
│       │   ├── 02_demand_analytics.py
│       │   ├── 03_supply_analytics.py
│       │   ├── 04_customer_journey.py
│       │   ├── 05_matching_efficiency.py
│       │   └── 06_financial_analytics.py
│       └── components/
│           ├── filters.py
│           ├── charts.py
│           └── kpi_cards.py
├── tests/
│   ├── test_schema.py
│   ├── test_seeds.py
│   └── test_models.py
├── scripts/
│   ├── setup_db.sh            # Database initialization
│   ├── run_models.sh          # Execute analytics models
│   └── deploy.sh              # Railway deployment
└── .github/
    └── workflows/
        └── ci.yml             # GitHub Actions CI/CD
```

---

## 🧱 Development Blocks (Resumable)

### Block 1: Foundation ✅
- [x] Project structure
- [x] CLAUDE.md, README.md, PROGRESS.md
- [x] Database schema design (schema.sql)

### Block 2: Data Layer
- [ ] Seed generator with Faker (realistic Brazilian textile data)
- [ ] Seed loader for PostgreSQL
- [ ] Docker Compose for local dev
- [ ] .env.example and Railway config

### Block 3: Staging Models
- [ ] All stg_ SQL models
- [ ] Data quality tests

### Block 4: Intermediate Models
- [ ] Business logic transformations
- [ ] Funnel stage mapping

### Block 5: Mart Models
- [ ] Platform KPIs
- [ ] Customer Journey
- [ ] Cohort Analysis
- [ ] CLV Model
- [ ] Oficina Scoring

### Block 6: Analytics & ML
- [ ] Bayesian CLV with PyMC
- [ ] Quality scoring algorithm
- [ ] Match optimization

### Block 7: Dashboards
- [ ] Streamlit multi-page app
- [ ] All 6 dashboard pages
- [ ] Interactive filters and charts

### Block 8: Deployment & CI/CD
- [ ] Railway deployment
- [ ] GitHub Actions
- [ ] Documentation finalization

---

## ⚙️ Tech Stack
| Layer | Technology |
|---|---|
| Database | PostgreSQL 16 (Railway) |
| Data Modeling | SQL + Python (dbt-style patterns) |
| Analytics | Python, Pandas, NumPy, SciPy |
| ML/Statistical | PyMC, scikit-learn |
| Dashboards | Streamlit |
| Deployment | Railway.com, GitHub Actions |
| Local Dev | Docker Compose, VS Code |
| AI-Assisted | Claude Code |

---

## 🇧🇷 Domain Context

### Textile Industry in Brazil
- Brazil is the 5th largest textile producer globally
- The industry is concentrated in SC (Blumenau region), SP, and CE
- Supply chain: Brands → Facções (sewing workshops) → Raw materials
- Key certifications: ABVTEX (responsible supply chain), NBCU, Disney

### Texlink Business Model
- **Two-sided marketplace**: Empresas ↔ Oficinas de Costura
- **Revenue**: Commission on matched orders (take-rate model)
- **BPO Service**: Supplier management outsourcing
- **Value prop for Empresas**: Find qualified workshops, reduce production time
- **Value prop for Oficinas**: Steady order flow, guaranteed payments, certifications

### Key Terminology
| Portuguese | English | Context |
|---|---|---|
| Empresa | Company/Brand | Demand side — places orders |
| Oficina de Costura | Sewing Workshop | Supply side — fulfills orders |
| Pedido | Order | Production order from empresa |
| Proposta | Proposal/Bid | Workshop bid on an order |
| Facção | Contract Manufacturer | Industry term for outsourced sewing |
| Peça | Piece/Garment | Unit of production |
| Lote | Batch/Lot | Group of pieces in production |
| Prazo | Deadline | Delivery timeline |
| Avaliação | Rating/Review | Quality assessment |
