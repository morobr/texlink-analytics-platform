# Technical Architecture — Texlink Analytics

> System design and data flow documentation.

---

## Overview

The Texlink Analytics Platform follows a **layered analytics architecture** inspired by dbt's modeling conventions, deployed on Railway's managed infrastructure.

```
┌─────────────────────────────────────────────────────────────┐
│                     RAILWAY PLATFORM                         │
│                                                              │
│  ┌──────────────┐         ┌──────────────────────────────┐  │
│  │ PostgreSQL 16 │────────▶│     Streamlit Dashboard      │  │
│  │              │         │     (6 pages, Altair/Plotly)  │  │
│  │  14 tables   │         └──────────────────────────────┘  │
│  │  11 stg views│                                           │
│  │   6 int views│         ┌──────────────────────────────┐  │
│  │   8 mart views│────────▶│    Analytics Engine (Python)  │  │
│  │              │         │  • CLV Model (BG/NBD)        │  │
│  └──────────────┘         │  • Quality Scoring           │  │
│                           │  • Match Optimization        │  │
│                           └──────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Source Layer (PostgreSQL Tables)
14 normalized tables storing transactional data. Schema defined in `src/database/schema.sql` with performance indexes in `indexes.sql` and business logic triggers in `functions.sql`.

### 2. Staging Layer (`stg_*` Views)
11 SQL views that provide:
- Type casting and null handling
- Column renaming to consistent conventions
- Basic derived fields (e.g., `is_active`, `days_since_signup`)
- 1:1 mapping with source tables

### 3. Intermediate Layer (`int_*` Views)
6 SQL views that join and transform staged data:
- `int_pedidos_enriched` — Full order context with empresa, oficina, and payment data
- `int_oficina_performance` — Aggregated workshop KPIs
- `int_empresa_activity` — Brand engagement metrics
- `int_funnel_stages` — Customer journey stage classification
- `int_match_pairs` — Historical empresa↔oficina pairings
- `int_daily_platform_snapshot` — Time-series daily aggregation

### 4. Marts Layer (`marts_*` Views)
8 analytical views consumed directly by dashboards:
- Platform KPIs, customer journey, cohort analysis, oficina scoring, CLV, match quality, revenue analytics, geographic analysis

### 5. Python Analytics Layer
Statistical and ML models in `src/analytics/`:
- **CLV Model** — BG/NBD + Gamma-Gamma via `lifetimes` library
- **Quality Scoring** — 6-dimension weighted composite with configurable weights
- **Match Optimization** — Constraint-based scoring with Hungarian algorithm
- **Cohort Analysis** — Retention and revenue matrices
- **Customer Journey** — Funnel analysis with stage timing

## Tech Stack Decisions

| Decision | Choice | Rationale |
|---|---|---|
| SQL views (not materialized) | PostgreSQL VIEWs | Simplicity; dataset size (~75k rows) doesn't need materialization overhead |
| dbt-style without dbt | Raw SQL files + Python runner | Showcase SQL skills directly; avoid framework abstraction for a portfolio project |
| Streamlit (not Superset/Metabase) | Streamlit | Full Python control, custom components, easy Railway deployment |
| lifetimes (not raw PyMC) | lifetimes library | Battle-tested BG/NBD implementation; PyMC listed for extensibility |
| Railway (not AWS/GCP) | Railway.com | One-click PostgreSQL + web service; free tier; fast iteration |
| Faker for seeds | faker + custom generators | Realistic Brazilian data (CPF, CNPJ, addresses, names) |

## Deployment

Railway auto-deploys from the `main` branch on GitHub push. The build process:

1. **Nixpacks** detects Python from `requirements.txt`
2. Installs all dependencies
3. Starts Streamlit via the command in `railway.toml`
4. Health check confirms the app responds at `/`

Database is provisioned as a separate Railway service, connected via `DATABASE_URL` environment variable (internal networking, no public exposure).
