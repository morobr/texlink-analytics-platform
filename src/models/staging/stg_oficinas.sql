-- ============================================================================
-- stg_oficinas — Staging model for oficinas (supply side)
-- ============================================================================

CREATE OR REPLACE VIEW stg_oficinas AS
SELECT
    id                                          AS oficina_id,
    razao_social,
    nome_fantasia,
    cnpj,
    LOWER(TRIM(email))                          AS email,
    REGEXP_REPLACE(telefone, '\D', '', 'g')     AS telefone_limpo,
    responsavel,

    -- Address
    TRIM(endereco)                              AS endereco,
    TRIM(cidade)                                AS cidade,
    UPPER(TRIM(estado))                         AS estado,
    REGEXP_REPLACE(cep, '\D', '', 'g')          AS cep_limpo,

    -- Capacity
    COALESCE(num_costureiras, 0)                AS num_costureiras,
    COALESCE(capacidade_mensal, 0)              AS capacidade_mensal_pecas,
    especialidades,
    maquinario,
    ARRAY_LENGTH(especialidades, 1)             AS num_especialidades,
    ARRAY_LENGTH(maquinario, 1)                 AS num_tipos_maquinario,

    -- Tier & scores
    tier,
    COALESCE(score_qualidade, 0)                AS score_qualidade,
    COALESCE(score_pontualidade, 0)             AS score_pontualidade,
    COALESCE(score_comunicacao, 0)              AS score_comunicacao,
    COALESCE(total_avaliacoes, 0)               AS total_avaliacoes,

    -- Composite score (equal-weight average)
    ROUND(
        (COALESCE(score_qualidade, 0) +
         COALESCE(score_pontualidade, 0) +
         COALESCE(score_comunicacao, 0)) / 3.0, 2
    )                                           AS score_medio,

    -- Status
    ativo,
    verificado,
    data_verificacao,

    CASE
        WHEN deleted_at IS NOT NULL THEN 'deletado'
        WHEN NOT ativo             THEN 'inativo'
        WHEN NOT verificado        THEN 'pendente_verificacao'
        ELSE 'ativo'
    END                                         AS status_cadastro,

    -- Timestamps
    created_at                                  AS dt_cadastro,
    updated_at                                  AS dt_atualizacao,
    deleted_at                                  AS dt_exclusao

FROM oficinas
WHERE deleted_at IS NULL
;
