-- ============================================================================
-- stg_empresas — Staging model for empresas (demand side)
-- Cleans, types, and standardizes empresa source records
-- ============================================================================

CREATE OR REPLACE VIEW stg_empresas AS
SELECT
    id                                          AS empresa_id,
    razao_social,
    nome_fantasia,
    cnpj,
    LOWER(TRIM(email))                          AS email,
    REGEXP_REPLACE(telefone, '\D', '', 'g')     AS telefone_limpo,
    website,
    logo_url,

    -- Address
    TRIM(endereco)                              AS endereco,
    TRIM(cidade)                                AS cidade,
    UPPER(TRIM(estado))                         AS estado,
    REGEXP_REPLACE(cep, '\D', '', 'g')          AS cep_limpo,

    -- Business
    porte,
    TRIM(segmento)                              AS segmento,
    COALESCE(volume_mensal, 0)                  AS volume_mensal_pecas,
    descricao,

    -- Status flags
    ativo,
    verificado,
    data_verificacao,

    -- Derived
    CASE
        WHEN deleted_at IS NOT NULL THEN 'deletado'
        WHEN NOT ativo             THEN 'inativo'
        WHEN NOT verificado        THEN 'pendente_verificacao'
        ELSE 'ativo'
    END                                         AS status_cadastro,

    -- Timestamps
    created_at                                  AS dt_cadastro,
    updated_at                                  AS dt_atualizacao,
    deleted_at                                  AS dt_exclusao,

    -- Metadata
    deleted_at IS NULL                          AS nao_deletado

FROM empresas
WHERE deleted_at IS NULL
;
