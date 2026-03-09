# Texlink Analytics — Plataforma de Dados Full-Stack

> Engenharia de analytics de ponta a ponta para um marketplace bilateral do setor textil, conectando marcas brasileiras a oficinas de costura qualificadas.

[![Demo ao Vivo](https://img.shields.io/badge/Demo%20ao%20Vivo-Railway-0B0D0E.svg)](https://texlink-analytics-production.up.railway.app)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E.svg)](https://railway.app/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Acesse: [texlink-analytics-production.up.railway.app](https://texlink-analytics-production.up.railway.app)**

---

## Sumario

- [Visao Geral](#visao-geral)
- [Arquitetura](#arquitetura)
- [Contexto de Negocio](#contexto-de-negocio)
- [Modelo de Dados](#modelo-de-dados)
- [Framework de Analytics](#framework-de-analytics)
- [Dashboards](#dashboards)
- [Como Executar](#como-executar)
- [Deploy](#deploy)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Autor](#autor)

---

## Visao Geral

Este projeto implementa uma **plataforma de analytics em nivel de producao** para a [Texlink](https://texlink.com.br), uma startup que esta transformando a cadeia de suprimentos textil brasileira conectando **Empresas** (marcas e confeccoes) a **Oficinas de Costura** (faccoes certificadas).

### O Que Este Projeto Demonstra

| Competencia | Implementacao |
|---|---|
| **Design de Banco de Dados** | Schema PostgreSQL normalizado com 14 tabelas, indices e triggers |
| **Engenharia de Dados** | Geracao de dados realistas com Faker para 500+ entidades |
| **Modelagem de Dados** | Modelos SQL em 3 camadas estilo dbt (staging -> intermediate -> marts) |
| **Analytics de Clientes** | Analise de funil completa, retencao por coorte, modelagem de CLV |
| **Analytics de Plataforma** | KPIs de marketplace bilateral, liquidez, eficiencia de matching |
| **Modelagem Estatistica** | Estimativa Bayesiana de CLV com PyMC |
| **Engenharia de ML** | Algoritmo de scoring de qualidade, predicao de churn |
| **Visualizacao** | Dashboard Streamlit com 6 paginas e filtros interativos |
| **DevOps** | Deploy no Railway, Docker Compose, CI/CD com GitHub Actions |

---

## Arquitetura

```
                    +----------------------------------+
                    |        Repositorio GitHub         |
                    |   (Source of Truth + CI/CD)       |
                    +----------+-----------------------+
                               |
                    +----------v-----------------------+
                    |        Railway.com                |
                    |  +---------+  +---------------+  |
                    |  |PostgreSQL|  |  Streamlit    |  |
                    |  |   DB    |  |  Dashboard    |  |
                    |  +----+----+  +-------+-------+  |
                    +-------+--------------+----------+
                            |               |
              +-------------v-------------+ |
              |     Motor de Analytics    | |
              |                           | |
              |  +---------------------+  | |
              |  |  Camada Staging     |  | |
              |  |  (modelos stg_*)    |  | |
              |  +---------+-----------+  | |
              |            v              | |
              |  +---------------------+  | |
              |  | Camada Intermediate  |  | |
              |  | (modelos int_*)     |  | |
              |  +---------+-----------+  | |
              |            v              | |
              |  +---------------------+  | |
              |  |   Camada Marts      |--+-+
              |  | (modelos marts_*)   |  |
              |  +---------------------+  |
              |            v              |
              |  +---------------------+  |
              |  |   Modelos ML /      |  |
              |  |   Estatisticos      |  |
              |  |  - CLV Bayesiano    |  |
              |  |  - Scoring          |  |
              |  |  - Otimizacao       |  |
              |  +---------------------+  |
              +---------------------------+
```

---

## Contexto de Negocio

### O Problema
A industria textil brasileira depende fortemente da producao terceirizada por pequenas oficinas de costura ("faccoes"). O processo de matching entre marcas e oficinas e manual, ineficiente e carece de garantia de qualidade — resultando em atrasos na producao, problemas de qualidade e altos custos de transacao.

### A Solucao da Texlink
Uma plataforma tecnologica que:
1. **Conecta** marcas a uma rede de oficinas de costura certificadas
2. **Gerencia** todo o ciclo de vida dos pedidos de producao
3. **Garante** qualidade atraves de scoring, certificacoes e monitoramento continuo
4. **Fornece** insights orientados por dados para tomada de decisao

### Dinamica do Marketplace Bilateral

```
  LADO DA DEMANDA              PLATAFORMA               LADO DA OFERTA
  +------------+            +--------------+           +--------------+
  | Empresas   |--pedidos-->|   Texlink    |<-propostas-|  Oficinas   |
  | (Marcas)   |            |  Motor de   |            | (Faccoes)   |
  |            |<-entregas--|  Matching    |--pedidos-->|             |
  |  ~200      |            |             |            |   ~500      |
  | ativas     |            |  Scoring    |            |  certificadas|
  +------------+            |  Analytics  |            +--------------+
                            +--------------+
```

---

## Modelo de Dados

### Visao Geral do Relacionamento entre Entidades

```
empresas --+-- usuarios ---- eventos_plataforma
           |
           +-- pedidos --+-- pedido_items
           |             |
           |             +-- propostas -- oficinas --+-- certificacoes
           |             |                          |
           |             +-- producao               +-- usuarios
           |             |                          |
           |             +-- avaliacoes             +-- categorias_produto
           |             |
           |             +-- pagamentos
           |
           +-- mensagens -- oficinas
```

### Decisoes de Design
- **Chaves substitutas** (UUID) para todas as entidades — portabilidade entre ambientes
- **Soft deletes** (campo `deleted_at`) — preserva historico para analytics
- **Event sourcing** em `eventos_plataforma` — reconstrucao completa do clickstream
- **Colunas temporais** (`created_at`, `updated_at`) — rastreamento de mudancas
- **Status baseados em enums** — maquinas de estado type-safe para pedidos/producao

---

## Framework de Analytics

### Camada 1: Modelos de Staging
Dados brutos limpos, tipados e renomeados seguindo convencoes consistentes.

### Camada 2: Modelos Intermediarios
| Modelo | Finalidade |
|---|---|
| `int_pedidos_enriched` | Pedidos com detalhes de empresa/oficina e financeiros |
| `int_oficina_performance` | Metricas agregadas de oficinas (qualidade, velocidade, volume) |
| `int_empresa_activity` | Metricas de engajamento e padroes de pedidos das empresas |
| `int_funnel_stages` | Mapeamento de cada empresa para seu estagio atual na jornada |

### Camada 3: Modelos Mart
| Modelo | Caso de Uso Analitico |
|---|---|
| `marts_platform_kpis` | Dashboard executivo — GMV, take rate, liquidez, crescimento |
| `marts_customer_journey` | Funil completo: cadastro -> ativacao -> retencao -> expansao |
| `marts_cohort_analysis` | Retencao mes a mes por coorte de cadastro |
| `marts_oficina_scoring` | Score composto de qualidade para ranking no marketplace |
| `marts_empresa_clv` | Estimativa Bayesiana de CLV por marca |
| `marts_match_quality` | Efetividade dos pareamentos empresa<->oficina |
| `marts_revenue_analytics` | Decomposicao de receita, unit economics |
| `marts_geographic_analysis` | Balanco regional de oferta e demanda |

### Modelos Estatisticos e de ML
| Modelo | Tecnica | Finalidade |
|---|---|---|
| **Estimativa de CLV** | BG/NBD + Gamma-Gamma (PyMC) | Prever valor futuro do cliente |
| **Scoring de Qualidade** | Composto ponderado + suavizacao Bayesiana | Ranquear confiabilidade das oficinas |
| **Otimizacao de Matching** | Scoring baseado em restricoes | Melhorar pareamento empresa<->oficina |
| **Predicao de Churn** | Analise de sobrevivencia | Identificar oficinas em risco |

---

## Dashboards

Seis paginas interativas em Streamlit cobrindo todo o espectro analitico:

| Pagina | Principais Visualizacoes |
|---|---|
| **Visao da Plataforma** | Cards de KPI, tendencia de GMV, metricas de crescimento, saude do marketplace |
| **Analytics de Demanda** | Segmentacao de empresas, padroes de pedidos, funil de ativacao |
| **Analytics de Oferta** | Capacidade das oficinas, certificacoes, distribuicao de qualidade |
| **Jornada do Cliente** | Diagrama Sankey, taxas de conversao do funil, tempo entre estagios |
| **Eficiencia de Matching** | Heatmap de match rate, cobertura geografica, gaps por categoria |
| **Analytics Financeiro** | Waterfall de receita, unit economics, curvas de LTV por coorte |

---

## Como Executar

### Pre-requisitos
- Python 3.11+
- PostgreSQL 16+ (ou Docker)
- Git

### Desenvolvimento Local

```bash
# 1. Clonar o repositorio
git clone https://github.com/morobr/texlink-analytics-platform.git
cd texlink-analytics-platform

# 2. Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Subir PostgreSQL (Docker)
docker-compose up -d postgres

# 5. Configurar variaveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais do banco

# 6. Inicializar banco e carregar dados seed
python -m src.seeds.seed_loader

# 7. Executar modelos de analytics
python -m src.models.run_all

# 8. Iniciar o dashboard
streamlit run src/dashboards/app.py
```

### Atalho: Script Completo

```bash
# Inicializar tudo de uma vez
./scripts/setup_db.sh
streamlit run src/dashboards/app.py
```

---

## Deploy

**URL de Producao:** [https://texlink-analytics-production.up.railway.app](https://texlink-analytics-production.up.railway.app)

### Servicos no Railway
| Servico | Tipo | Status |
|---|---|---|
| `Postgres` | PostgreSQL 16 | Ativo |
| `texlink-analytics` | Streamlit (nixpacks) | Ativo |

### Variaveis de Ambiente
```
DATABASE_URL=postgresql://user:pass@host:port/dbname
PGHOST=...
PGPORT=5432
PGDATABASE=railway
PGUSER=...
PGPASSWORD=...
```

---

## Estrutura do Projeto

```
texlink-analytics-platform/
├── README.md              # Documentacao (EN)
├── README.pt-br.md        # Documentacao (PT-BR)
├── PROGRESS.md            # Rastreamento de progresso
├── LICENSE                # Licenca MIT
├── requirements.txt       # Dependencias Python
├── docker-compose.yml     # PostgreSQL local
├── railway.toml           # Config Railway
├── .env.example           # Template de variaveis
├── docs/
│   ├── data_dictionary.md     # Dicionario de dados
│   ├── business_glossary.md   # Glossario de negocios
│   └── architecture.md        # Arquitetura tecnica
├── src/
│   ├── database/          # DDL do schema + indices
│   ├── seeds/             # Geracao de dados
│   ├── models/            # Transformacoes SQL
│   ├── analytics/         # Analytics Python + ML
│   └── dashboards/        # Aplicacao Streamlit
├── tests/                 # Suite de testes Pytest
├── scripts/               # Utilitarios shell
└── .github/workflows/     # CI/CD
```

---

## Stack Tecnologica

| Camada | Tecnologia |
|---|---|
| Banco de Dados | PostgreSQL 16 (Railway) |
| Modelagem | SQL + Python (padroes dbt) |
| Analytics | Python, Pandas, NumPy, SciPy |
| ML/Estatistica | PyMC, scikit-learn, lifetimes |
| Dashboards | Streamlit, Altair, Plotly |
| Deploy | Railway.com, GitHub Actions |
| Dev Local | Docker Compose |

---

## Desenvolvimento Assistido por IA

Este projeto foi desenvolvido utilizando **ferramentas assistidas por IA** ([Claude Code](https://claude.ai)) para acelerar a implementacao. As decisoes de arquitetura, logica de negocio, modelagem de dominio e framework de analytics refletem minha experiencia como engenheiro de analytics — a IA serviu como multiplicador de velocidade na codificacao.

O que eu trouxe:
- **Expertise de dominio**: Dinamicas de marketplace textil, KPIs de plataforma bilateral, contexto da industria brasileira (ABVTEX, faccoes, LGPD)
- **Design de arquitetura**: Decisoes de modelagem de dados (staging/intermediate/marts), definicoes de metricas, algoritmos de scoring
- **Garantia de qualidade**: Code review, estrategia de testes, troubleshooting de deploy

O que a IA acelerou:
- Geracao de codigo boilerplate (views SQL, scaffolding de paginas Streamlit)
- Elaboracao de documentacao
- Gerenciamento de dependencias e configuracao de deploy

Isso reflete a realidade moderna da engenharia de software — a capacidade de direcionar ferramentas de IA de forma eficaz e, por si so, uma competencia essencial.

---

## Autor

**Moro** — Analytics Engineer & Data Scientist

Especializado em modern data stack (Databricks, dbt, Python, PyMC), marketing analytics e privacidade de dados (LGPD). Construindo solucoes data-driven para o mercado brasileiro.

---

*Conectando o futuro da industria textil brasileira*
