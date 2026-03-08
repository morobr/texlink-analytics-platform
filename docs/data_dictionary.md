# Data Dictionary — Texlink Analytics

> Complete schema documentation for all 14 source tables, 11 staging views, 6 intermediate views, and 8 mart views.

---

## Source Tables

### empresas
Brand/contractor companies registered on the platform.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| razao_social | VARCHAR(255) | Legal company name |
| nome_fantasia | VARCHAR(255) | Trade name |
| cnpj | VARCHAR(18) | Brazilian tax ID (CNPJ) |
| email | VARCHAR(255) | Contact email |
| telefone | VARCHAR(20) | Phone number |
| estado | VARCHAR(2) | State code (SP, SC, CE, etc.) |
| cidade | VARCHAR(100) | City |
| segmento | empresa_segmento | Industry segment enum |
| porte | empresa_porte | Company size enum |
| ativo | BOOLEAN | Active status |
| created_at | TIMESTAMP | Registration date |
| updated_at | TIMESTAMP | Last update |
| deleted_at | TIMESTAMP | Soft delete timestamp |

### oficinas
Sewing workshops (service providers).

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| nome | VARCHAR(255) | Workshop name |
| cnpj | VARCHAR(18) | Brazilian tax ID |
| email | VARCHAR(255) | Contact email |
| telefone | VARCHAR(20) | Phone number |
| estado | VARCHAR(2) | State code |
| cidade | VARCHAR(100) | City |
| capacidade_mensal | INTEGER | Monthly production capacity (pieces) |
| especialidades | TEXT[] | Array of specialties |
| nota_qualidade | DECIMAL(3,2) | Quality score (0-5) |
| ativo | BOOLEAN | Active status |
| created_at | TIMESTAMP | Registration date |
| updated_at | TIMESTAMP | Last update |
| deleted_at | TIMESTAMP | Soft delete timestamp |

### pedidos
Production orders placed by empresas.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| empresa_id | UUID | FK → empresas |
| oficina_id | UUID | FK → oficinas (assigned workshop) |
| status | pedido_status | Order status enum |
| valor_total | DECIMAL(12,2) | Total order value (BRL) |
| quantidade_pecas | INTEGER | Total pieces in order |
| prazo_entrega | DATE | Delivery deadline |
| created_at | TIMESTAMP | Order creation date |
| updated_at | TIMESTAMP | Last status change |

### propostas
Proposals/bids from oficinas on pedidos.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| pedido_id | UUID | FK → pedidos |
| oficina_id | UUID | FK → oficinas |
| valor | DECIMAL(12,2) | Proposed value (BRL) |
| prazo_dias | INTEGER | Proposed delivery days |
| status | proposta_status | Proposal status enum |
| created_at | TIMESTAMP | Submission date |

### pagamentos
Payment transactions.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| pedido_id | UUID | FK → pedidos |
| valor | DECIMAL(12,2) | Payment amount (BRL) |
| taxa_plataforma | DECIMAL(12,2) | Platform fee (BRL) |
| metodo | VARCHAR(50) | Payment method |
| status | pagamento_status | Payment status enum |
| data_pagamento | TIMESTAMP | Payment date |
| created_at | TIMESTAMP | Record creation |

### avaliacoes
Quality ratings and reviews.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| pedido_id | UUID | FK → pedidos |
| avaliador_tipo | VARCHAR(20) | Reviewer type (empresa/oficina) |
| nota | INTEGER | Rating (1-5) |
| comentario | TEXT | Review text |
| created_at | TIMESTAMP | Review date |

### producao
Production tracking per order.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| pedido_id | UUID | FK → pedidos |
| etapa | producao_etapa | Production stage enum |
| quantidade_produzida | INTEGER | Pieces produced |
| quantidade_aprovada | INTEGER | Pieces approved QC |
| data_inicio | TIMESTAMP | Stage start date |
| data_fim | TIMESTAMP | Stage end date |

### certificacoes
Workshop certifications (ABVTEX, NBCU, Disney, etc.).

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| oficina_id | UUID | FK → oficinas |
| tipo | VARCHAR(50) | Certification type |
| data_emissao | DATE | Issue date |
| data_validade | DATE | Expiry date |
| ativo | BOOLEAN | Currently valid |

### usuarios, mensagens, eventos_plataforma, categorias_produto, notificacoes, pedido_items
See `src/database/schema.sql` for full column definitions.

---

## Analytics Views

### Staging Layer (stg_*)
1:1 with source tables. Clean, cast, rename. See `src/models/staging/`.

### Intermediate Layer (int_*)
Business logic joins. See `src/models/intermediate/`.

### Marts Layer (marts_*)
Analytics-ready aggregations. See `src/models/marts/`.
