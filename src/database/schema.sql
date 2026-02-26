-- ============================================================================
-- TEXLINK ANALYTICS — PostgreSQL Schema
-- Version: 1.0.0
-- Description: Full DDL for Texlink textile marketplace platform
-- Target: PostgreSQL 16+ on Railway.com
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- Trigram for fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gist";    -- For exclusion constraints

-- ============================================================================
-- ENUMS — Type-safe status machines
-- ============================================================================

CREATE TYPE user_role AS ENUM ('admin', 'empresa_owner', 'empresa_user', 'oficina_owner', 'oficina_user');
CREATE TYPE empresa_size AS ENUM ('micro', 'pequena', 'media', 'grande');
CREATE TYPE oficina_tier AS ENUM ('bronze', 'prata', 'ouro', 'diamante');
CREATE TYPE pedido_status AS ENUM (
    'rascunho',          -- Draft
    'publicado',         -- Published / Open for proposals
    'em_negociacao',     -- Negotiating with workshop(s)
    'confirmado',        -- Order confirmed / Matched
    'em_producao',       -- In production
    'controle_qualidade',-- Quality control
    'entregue',          -- Delivered
    'finalizado',        -- Completed (payment done)
    'cancelado',         -- Cancelled
    'disputa'            -- In dispute
);
CREATE TYPE proposta_status AS ENUM ('enviada', 'em_analise', 'aceita', 'recusada', 'expirada', 'retirada');
CREATE TYPE producao_status AS ENUM ('aguardando_material', 'em_corte', 'em_costura', 'em_acabamento', 'controle_qualidade', 'embalagem', 'expedido');
CREATE TYPE pagamento_status AS ENUM ('pendente', 'processando', 'aprovado', 'pago', 'estornado', 'falha');
CREATE TYPE pagamento_metodo AS ENUM ('pix', 'boleto', 'transferencia', 'cartao_credito');
CREATE TYPE certificacao_tipo AS ENUM ('abvtex', 'nbcu', 'disney', 'bsci', 'wrap', 'iso9001', 'oeko_tex', 'gots', 'outras');
CREATE TYPE evento_tipo AS ENUM (
    'page_view', 'signup_started', 'signup_completed', 'login',
    'profile_updated', 'search_performed', 'oficina_viewed',
    'pedido_created', 'pedido_published', 'proposta_sent',
    'proposta_viewed', 'proposta_aceita', 'mensagem_sent',
    'pagamento_initiated', 'avaliacao_submitted', 'certificacao_uploaded',
    'relatorio_viewed', 'export_data', 'logout'
);

-- ============================================================================
-- TABLE: categorias_produto
-- Product categories in the textile industry
-- ============================================================================
CREATE TABLE categorias_produto (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome            VARCHAR(100) NOT NULL UNIQUE,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    descricao       TEXT,
    parent_id       UUID REFERENCES categorias_produto(id),
    nivel           SMALLINT NOT NULL DEFAULT 1,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE categorias_produto IS 'Hierarchical product categories for textile production (e.g., Camisetas > Camisetas Polo)';

-- ============================================================================
-- TABLE: empresas
-- Demand side — brands and companies that place production orders
-- ============================================================================
CREATE TABLE empresas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    razao_social    VARCHAR(255) NOT NULL,
    nome_fantasia   VARCHAR(255) NOT NULL,
    cnpj            VARCHAR(18) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL,
    telefone        VARCHAR(20),
    website         VARCHAR(255),
    logo_url        VARCHAR(500),

    -- Address
    endereco        VARCHAR(255),
    cidade          VARCHAR(100),
    estado          VARCHAR(2),
    cep             VARCHAR(10),

    -- Business details
    porte           empresa_size NOT NULL DEFAULT 'micro',
    segmento        VARCHAR(100),        -- e.g., "Moda Feminina", "Uniformes"
    volume_mensal   INTEGER,             -- Expected monthly piece volume
    descricao       TEXT,

    -- Platform status
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    verificado      BOOLEAN NOT NULL DEFAULT FALSE,
    data_verificacao TIMESTAMPTZ,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

COMMENT ON TABLE empresas IS 'Demand side: Fashion brands and textile companies that post production orders';

-- ============================================================================
-- TABLE: oficinas
-- Supply side — sewing workshops that fulfill orders
-- ============================================================================
CREATE TABLE oficinas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    razao_social    VARCHAR(255) NOT NULL,
    nome_fantasia   VARCHAR(255) NOT NULL,
    cnpj            VARCHAR(18) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL,
    telefone        VARCHAR(20),
    responsavel     VARCHAR(255),        -- Workshop owner/manager name
    logo_url        VARCHAR(500),

    -- Address
    endereco        VARCHAR(255),
    cidade          VARCHAR(100),
    estado          VARCHAR(2),
    cep             VARCHAR(10),

    -- Capacity & capabilities
    num_costureiras INTEGER,             -- Number of seamstresses
    capacidade_mensal INTEGER,           -- Monthly capacity in pieces
    especialidades  TEXT[],              -- Array of specialties
    maquinario      TEXT[],              -- Array of machinery types
    tier            oficina_tier NOT NULL DEFAULT 'bronze',

    -- Scoring
    score_qualidade  NUMERIC(4,2) DEFAULT 0.00,  -- 0-10 composite score
    score_pontualidade NUMERIC(4,2) DEFAULT 0.00,
    score_comunicacao NUMERIC(4,2) DEFAULT 0.00,
    total_avaliacoes INTEGER DEFAULT 0,

    -- Platform status
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    verificado      BOOLEAN NOT NULL DEFAULT FALSE,
    data_verificacao TIMESTAMPTZ,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

COMMENT ON TABLE oficinas IS 'Supply side: Sewing workshops (facções) that fulfill production orders';

-- ============================================================================
-- TABLE: usuarios
-- Platform users linked to empresas or oficinas
-- ============================================================================
CREATE TABLE usuarios (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    nome            VARCHAR(255) NOT NULL,
    telefone        VARCHAR(20),
    role            user_role NOT NULL,
    avatar_url      VARCHAR(500),

    -- Foreign keys (one of these is set based on role)
    empresa_id      UUID REFERENCES empresas(id),
    oficina_id      UUID REFERENCES oficinas(id),

    -- Auth & activity
    ultimo_login    TIMESTAMPTZ,
    login_count     INTEGER DEFAULT 0,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT chk_user_entity CHECK (
        (role IN ('empresa_owner', 'empresa_user') AND empresa_id IS NOT NULL AND oficina_id IS NULL) OR
        (role IN ('oficina_owner', 'oficina_user') AND oficina_id IS NOT NULL AND empresa_id IS NULL) OR
        (role = 'admin' AND empresa_id IS NULL AND oficina_id IS NULL)
    )
);

COMMENT ON TABLE usuarios IS 'Platform users with role-based access linked to either an empresa or oficina';

-- ============================================================================
-- TABLE: pedidos
-- Production orders placed by empresas
-- ============================================================================
CREATE TABLE pedidos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo          VARCHAR(20) NOT NULL UNIQUE,  -- Human-readable order code (e.g., PED-2025-0001)
    empresa_id      UUID NOT NULL REFERENCES empresas(id),
    oficina_id      UUID REFERENCES oficinas(id), -- Set after matching

    -- Order details
    titulo          VARCHAR(255) NOT NULL,
    descricao       TEXT,
    categoria_id    UUID REFERENCES categorias_produto(id),
    quantidade_total INTEGER NOT NULL,
    unidade         VARCHAR(20) DEFAULT 'peças',

    -- Financials
    valor_estimado  NUMERIC(12,2),               -- Empresa's budget estimate
    valor_final     NUMERIC(12,2),               -- Agreed price after negotiation
    moeda           VARCHAR(3) DEFAULT 'BRL',

    -- Timeline
    data_publicacao TIMESTAMPTZ,
    data_limite_propostas TIMESTAMPTZ,
    prazo_entrega   DATE,
    data_entrega_real DATE,

    -- Status
    status          pedido_status NOT NULL DEFAULT 'rascunho',
    prioridade      SMALLINT DEFAULT 3 CHECK (prioridade BETWEEN 1 AND 5),

    -- Metadata
    observacoes     TEXT,
    anexos_urls     TEXT[],

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

COMMENT ON TABLE pedidos IS 'Production orders — the core transaction unit of the marketplace';

-- ============================================================================
-- TABLE: pedido_items
-- Line items within each order
-- ============================================================================
CREATE TABLE pedido_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pedido_id       UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,

    descricao       VARCHAR(255) NOT NULL,
    quantidade      INTEGER NOT NULL,
    tamanho         VARCHAR(10),          -- P, M, G, GG, etc.
    cor             VARCHAR(50),
    material        VARCHAR(100),
    valor_unitario  NUMERIC(10,2),
    observacoes     TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE pedido_items IS 'Individual line items (SKUs) within a production order';

-- ============================================================================
-- TABLE: propostas
-- Proposals/bids from oficinas on orders
-- ============================================================================
CREATE TABLE propostas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pedido_id       UUID NOT NULL REFERENCES pedidos(id),
    oficina_id      UUID NOT NULL REFERENCES oficinas(id),

    -- Proposal details
    valor_proposto  NUMERIC(12,2) NOT NULL,
    prazo_proposto  DATE NOT NULL,
    descricao       TEXT,
    condicoes       TEXT,

    -- Status
    status          proposta_status NOT NULL DEFAULT 'enviada',
    data_resposta   TIMESTAMPTZ,
    motivo_recusa   TEXT,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate proposals
    UNIQUE(pedido_id, oficina_id)
);

COMMENT ON TABLE propostas IS 'Workshop bids on production orders — the matching mechanism';

-- ============================================================================
-- TABLE: producao
-- Production tracking and progress updates
-- ============================================================================
CREATE TABLE producao (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pedido_id       UUID NOT NULL REFERENCES pedidos(id),
    oficina_id      UUID NOT NULL REFERENCES oficinas(id),

    -- Production progress
    status          producao_status NOT NULL DEFAULT 'aguardando_material',
    percentual_concluido NUMERIC(5,2) DEFAULT 0.00,

    -- Quantities
    quantidade_produzida INTEGER DEFAULT 0,
    quantidade_aprovada  INTEGER DEFAULT 0,
    quantidade_rejeitada INTEGER DEFAULT 0,

    -- Timeline
    data_inicio     TIMESTAMPTZ,
    data_previsao   DATE,
    data_conclusao  TIMESTAMPTZ,

    -- Quality
    observacoes_qualidade TEXT,
    fotos_producao  TEXT[],

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE producao IS 'Production progress tracking — stage-by-stage monitoring';

-- ============================================================================
-- TABLE: avaliacoes
-- Quality ratings and reviews (bidirectional)
-- ============================================================================
CREATE TABLE avaliacoes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pedido_id       UUID NOT NULL REFERENCES pedidos(id),

    -- Who is rating whom
    avaliador_id    UUID NOT NULL REFERENCES usuarios(id),
    avaliado_empresa_id UUID REFERENCES empresas(id),
    avaliado_oficina_id UUID REFERENCES oficinas(id),

    -- Ratings (1-5 stars)
    nota_geral      SMALLINT NOT NULL CHECK (nota_geral BETWEEN 1 AND 5),
    nota_qualidade  SMALLINT CHECK (nota_qualidade BETWEEN 1 AND 5),
    nota_pontualidade SMALLINT CHECK (nota_pontualidade BETWEEN 1 AND 5),
    nota_comunicacao SMALLINT CHECK (nota_comunicacao BETWEEN 1 AND 5),
    nota_custo_beneficio SMALLINT CHECK (nota_custo_beneficio BETWEEN 1 AND 5),

    -- Review
    comentario      TEXT,
    publica         BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One review per direction per order
    UNIQUE(pedido_id, avaliador_id),

    -- Must rate either empresa or oficina
    CONSTRAINT chk_avaliado CHECK (
        (avaliado_empresa_id IS NOT NULL AND avaliado_oficina_id IS NULL) OR
        (avaliado_empresa_id IS NULL AND avaliado_oficina_id IS NOT NULL)
    )
);

COMMENT ON TABLE avaliacoes IS 'Bidirectional ratings — empresas rate oficinas and vice versa';

-- ============================================================================
-- TABLE: certificacoes
-- Workshop certifications and compliance documents
-- ============================================================================
CREATE TABLE certificacoes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    oficina_id      UUID NOT NULL REFERENCES oficinas(id),

    tipo            certificacao_tipo NOT NULL,
    nome            VARCHAR(255) NOT NULL,
    entidade_emissora VARCHAR(255),
    numero_certificado VARCHAR(100),

    -- Validity
    data_emissao    DATE NOT NULL,
    data_validade   DATE,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,

    -- Documents
    documento_url   VARCHAR(500),
    verificado      BOOLEAN DEFAULT FALSE,
    data_verificacao TIMESTAMPTZ,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE certificacoes IS 'Industry certifications held by workshops (ABVTEX, NBCU, Disney, etc.)';

-- ============================================================================
-- TABLE: pagamentos
-- Payment transactions
-- ============================================================================
CREATE TABLE pagamentos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pedido_id       UUID NOT NULL REFERENCES pedidos(id),
    empresa_id      UUID NOT NULL REFERENCES empresas(id),
    oficina_id      UUID NOT NULL REFERENCES oficinas(id),

    -- Financial
    valor_bruto     NUMERIC(12,2) NOT NULL,
    taxa_plataforma NUMERIC(12,2) NOT NULL,  -- Texlink's commission
    valor_liquido   NUMERIC(12,2) NOT NULL,  -- Amount paid to oficina
    percentual_taxa NUMERIC(5,2) NOT NULL,   -- Commission percentage

    metodo          pagamento_metodo NOT NULL DEFAULT 'pix',
    status          pagamento_status NOT NULL DEFAULT 'pendente',

    -- External references
    referencia_externa VARCHAR(100),          -- Payment gateway reference
    comprovante_url VARCHAR(500),

    -- Timeline
    data_vencimento DATE,
    data_pagamento  TIMESTAMPTZ,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE pagamentos IS 'Financial transactions — tracks platform take-rate and payment lifecycle';

-- ============================================================================
-- TABLE: mensagens
-- In-platform messaging between empresas and oficinas
-- ============================================================================
CREATE TABLE mensagens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    remetente_id    UUID NOT NULL REFERENCES usuarios(id),
    destinatario_id UUID NOT NULL REFERENCES usuarios(id),
    pedido_id       UUID REFERENCES pedidos(id),  -- Optional context

    conteudo        TEXT NOT NULL,
    lida            BOOLEAN DEFAULT FALSE,
    data_leitura    TIMESTAMPTZ,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Cannot message yourself
    CONSTRAINT chk_not_self CHECK (remetente_id != destinatario_id)
);

COMMENT ON TABLE mensagens IS 'Platform messaging — communication between marketplace participants';

-- ============================================================================
-- TABLE: eventos_plataforma
-- Platform event log — clickstream and activity tracking
-- ============================================================================
CREATE TABLE eventos_plataforma (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id      UUID REFERENCES usuarios(id),      -- NULL for anonymous events
    session_id      VARCHAR(64),

    -- Event details
    tipo            evento_tipo NOT NULL,
    pagina          VARCHAR(255),
    referrer        VARCHAR(255),

    -- Context
    entidade_tipo   VARCHAR(50),     -- 'pedido', 'oficina', 'empresa', etc.
    entidade_id     UUID,
    metadata        JSONB DEFAULT '{}',

    -- Device & location
    ip_address      INET,
    user_agent      TEXT,
    dispositivo     VARCHAR(20),     -- 'desktop', 'mobile', 'tablet'

    -- Timestamp (partitioning key)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE eventos_plataforma IS 'Platform clickstream — full user activity log for analytics';

-- ============================================================================
-- TABLE: notificacoes
-- System notifications sent to users
-- ============================================================================
CREATE TABLE notificacoes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id      UUID NOT NULL REFERENCES usuarios(id),

    titulo          VARCHAR(255) NOT NULL,
    conteudo        TEXT NOT NULL,
    tipo            VARCHAR(50) NOT NULL,  -- 'pedido_update', 'proposta_nova', 'pagamento', etc.
    canal           VARCHAR(20) DEFAULT 'plataforma',  -- 'plataforma', 'email', 'push', 'whatsapp'

    -- References
    entidade_tipo   VARCHAR(50),
    entidade_id     UUID,

    -- Status
    lida            BOOLEAN DEFAULT FALSE,
    data_leitura    TIMESTAMPTZ,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE notificacoes IS 'System notifications — tracks multi-channel communication to users';
