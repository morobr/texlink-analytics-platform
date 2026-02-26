# 🧵 Texlink Analytics — Full-Stack Data Platform

> End-to-end analytics engineering for a two-sided textile marketplace connecting Brazilian brands to qualified sewing workshops.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway-0B0D0E.svg)](https://texlink-analytics-production.up.railway.app)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E.svg)](https://railway.app/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**🚀 Live at: [texlink-analytics-production.up.railway.app](https://texlink-analytics-production.up.railway.app)**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Business Context](#business-context)
- [Data Model](#data-model)
- [Analytics Framework](#analytics-framework)
- [Dashboards](#dashboards)
- [Getting Started](#getting-started)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Author](#author)

---

## Overview

This project implements a **production-grade analytics platform** for [Texlink](https://texlink.com.br), a startup that transforms the Brazilian textile supply chain by connecting **Empresas** (fashion brands and manufacturers) with **Oficinas de Costura** (certified sewing workshops).

### What This Project Demonstrates

| Capability | Implementation |
|---|---|
| **Database Design** | Normalized PostgreSQL schema with 14 tables, indexes, and triggers |
| **Data Engineering** | Realistic seed data generation with Faker for 500+ entities |
| **Data Modeling** | 3-layer dbt-style SQL models (staging → intermediate → marts) |
| **Customer Analytics** | Full funnel analysis, cohort retention, CLV modeling |
| **Platform Analytics** | Two-sided marketplace KPIs, liquidity, matching efficiency |
| **Statistical Modeling** | Bayesian CLV estimation with PyMC |
| **ML Engineering** | Quality scoring algorithm, churn prediction |
| **Visualization** | 6-page Streamlit dashboard with interactive filters |
| **DevOps** | Railway deployment, Docker Compose, GitHub Actions CI/CD |

---

## Architecture

```
                    ┌──────────────────────────────────┐
                    │        GitHub Repository          │
                    │   (Source of Truth + CI/CD)       │
                    └──────────┬───────────────────────┘
                               │
                    ┌──────────▼───────────────────────┐
                    │        Railway.com                │
                    │  ┌─────────┐  ┌───────────────┐  │
                    │  │PostgreSQL│  │  Streamlit    │  │
                    │  │   DB    │  │  Dashboard    │  │
                    │  └────┬────┘  └───────┬───────┘  │
                    └───────┼───────────────┼──────────┘
                            │               │
              ┌─────────────▼─────────────┐ │
              │     Analytics Engine       │ │
              │                           │ │
              │  ┌─────────────────────┐  │ │
              │  │   Staging Layer     │  │ │
              │  │   (stg_* models)    │  │ │
              │  └─────────┬───────────┘  │ │
              │            ▼              │ │
              │  ┌─────────────────────┐  │ │
              │  │ Intermediate Layer   │  │ │
              │  │ (int_* models)      │  │ │
              │  └─────────┬───────────┘  │ │
              │            ▼              │ │
              │  ┌─────────────────────┐  │ │
              │  │   Marts Layer       │──┼─┘
              │  │ (marts_* models)    │  │
              │  └─────────────────────┘  │
              │            ▼              │
              │  ┌─────────────────────┐  │
              │  │   ML / Statistical  │  │
              │  │   Models            │  │
              │  │  • Bayesian CLV     │  │
              │  │  • Quality Scoring  │  │
              │  │  • Match Optimizer  │  │
              │  └─────────────────────┘  │
              └───────────────────────────┘
```

---

## Business Context

### The Problem
Brazil's textile industry relies heavily on outsourced production through small sewing workshops ("facções"). The matching process between brands and workshops is manual, inefficient, and lacks quality assurance — leading to production delays, quality issues, and high transaction costs.

### Texlink's Solution
A technology platform that:
1. **Connects** brands to a network of certified sewing workshops
2. **Manages** the entire production order lifecycle
3. **Ensures** quality through scoring, certifications, and continuous monitoring
4. **Provides** data-driven insights for decision making

### Two-Sided Marketplace Dynamics

```
  DEMAND SIDE                  PLATFORM                 SUPPLY SIDE
  ┌──────────┐            ┌──────────────┐           ┌──────────────┐
  │ Empresas │──pedidos──▶│   Texlink    │◀─propostas─│  Oficinas   │
  │ (Brands) │            │  Matching    │            │ (Workshops) │
  │          │◀─delivery──│  Engine      │──orders───▶│             │
  │  ~200    │            │             │            │   ~500      │
  │ active   │            │  Quality    │            │  certified  │
  └──────────┘            │  Scoring    │            └──────────────┘
                          │  Analytics  │
                          └──────────────┘
```

---

## Data Model

### Entity-Relationship Overview

```
empresas ──┬── usuarios ──── eventos_plataforma
           │
           ├── pedidos ──┬── pedido_items
           │             │
           │             ├── propostas ── oficinas ──┬── certificacoes
           │             │                          │
           │             ├── producao               ├── usuarios
           │             │                          │
           │             ├── avaliacoes             └── categorias_produto
           │             │
           │             └── pagamentos
           │
           └── mensagens ── oficinas
```

### Key Design Decisions
- **Surrogate keys** (UUID) for all entities — portable across environments
- **Soft deletes** (`deleted_at` timestamp) — preserves analytics history
- **Event sourcing** on `eventos_plataforma` — full clickstream reconstruction
- **Temporal columns** (`created_at`, `updated_at`) — enables change tracking
- **Enum-based status fields** — type-safe state machines for orders/production

---

## Analytics Framework

### Layer 1: Staging Models
Raw source data cleaned, typed, and renamed following consistent conventions.

### Layer 2: Intermediate Models
| Model | Purpose |
|---|---|
| `int_pedidos_enriched` | Orders joined with empresa/oficina details and financials |
| `int_oficina_performance` | Aggregated workshop metrics (quality, speed, volume) |
| `int_empresa_activity` | Brand engagement and ordering patterns |
| `int_funnel_stages` | Maps each empresa to their current journey stage |

### Layer 3: Mart Models
| Model | Analytics Use Case |
|---|---|
| `marts_platform_kpis` | Executive dashboard — GMV, take rate, liquidity, growth |
| `marts_customer_journey` | Full funnel: signup → activation → retention → expansion |
| `marts_cohort_analysis` | Month-over-month retention by signup cohort |
| `marts_oficina_scoring` | Composite quality score driving marketplace ranking |
| `marts_empresa_clv` | Bayesian CLV estimation per brand |
| `marts_match_quality` | Effectiveness of empresa↔oficina pairings |
| `marts_revenue_analytics` | Revenue decomposition, unit economics |
| `marts_geographic_analysis` | Regional supply-demand balance |

### Statistical & ML Models
| Model | Technique | Purpose |
|---|---|---|
| **CLV Estimation** | BG/NBD + Gamma-Gamma (PyMC) | Predict future customer value |
| **Quality Scoring** | Weighted composite + Bayesian smoothing | Rank workshop reliability |
| **Match Optimization** | Constraint-based scoring | Improve empresa↔oficina pairing |
| **Churn Prediction** | Survival analysis | Identify at-risk workshops |

---

## Dashboards

Six interactive Streamlit pages covering the full analytics spectrum:

| Page | Key Visuals |
|---|---|
| **Platform Overview** | KPI cards, GMV trend, growth metrics, marketplace health |
| **Demand Analytics** | Empresa segmentation, order patterns, activation funnel |
| **Supply Analytics** | Workshop capacity, certifications, quality distribution |
| **Customer Journey** | Sankey diagram, funnel conversion rates, time-between-stages |
| **Matching Efficiency** | Match rate heatmap, geographic coverage, category gaps |
| **Financial Analytics** | Revenue waterfall, unit economics, cohort LTV curves |

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 16+ (or Docker)
- Git

### Local Development

```bash
# 1. Clone the repository
git clone https://github.com/morobr/texlink-analytics-platform.git
cd texlink-analytics

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start PostgreSQL (Docker)
docker-compose up -d postgres

# 5. Set up environment variables
cp .env.example .env
# Edit .env with your database credentials

# 6. Initialize database and load seed data
python -m src.seeds.seed_loader

# 7. Run analytics models
python -m src.models.run_all

# 8. Launch dashboard
streamlit run src/dashboards/app.py
```

### Railway Deployment

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login and link project
railway login
railway link

# 3. Deploy
railway up
```

---

## Deployment

**Live URL:** [https://texlink-analytics-production.up.railway.app](https://texlink-analytics-production.up.railway.app)

### Railway Services
| Service | Type | Status |
|---|---|---|
| `Postgres` | PostgreSQL 16 | Running |
| `texlink-analytics` | Streamlit (nixpacks) | Running |

### Environment Variables
```
DATABASE_URL=postgresql://user:pass@host:port/dbname
PGHOST=...
PGPORT=5432
PGDATABASE=railway
PGUSER=...
PGPASSWORD=...
```

---

## Project Structure

```
texlink-analytics/
├── CLAUDE.md              # AI development guide
├── README.md              # This file
├── PROGRESS.md            # Task tracking
├── requirements.txt       # Dependencies
├── docker-compose.yml     # Local PostgreSQL
├── railway.toml           # Railway config
├── .env.example           # Env template
├── docs/                  # Documentation
├── src/
│   ├── database/          # Schema DDL + indexes
│   ├── seeds/             # Data generation
│   ├── models/            # SQL transformations
│   ├── analytics/         # Python analytics + ML
│   └── dashboards/        # Streamlit app
├── tests/                 # Pytest suite
├── scripts/               # Shell utilities
└── .github/workflows/     # CI/CD
```

---

## Author

**Moro** — Analytics Engineer & Data Scientist

Specialized in modern data stack (Databricks, dbt, Python, PyMC), marketing analytics, and data privacy (LGPD). Building data-driven solutions for the Brazilian market.

---

*Built with ❤️ for Texlink — Conectando o futuro da indústria têxtil*
