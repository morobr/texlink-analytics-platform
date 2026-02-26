-- ============================================================================
-- stg_certificacoes — Staging model for workshop certifications
-- ============================================================================

CREATE OR REPLACE VIEW stg_certificacoes AS
SELECT
    c.id                                        AS certificacao_id,
    c.oficina_id,
    c.tipo,
    TRIM(c.nome)                                AS nome,
    c.entidade_emissora,
    c.numero_certificado,

    -- Validity
    c.data_emissao,
    c.data_validade,
    c.ativo,

    -- Derived validity status
    CASE
        WHEN c.data_validade IS NULL        THEN 'sem_validade'
        WHEN c.data_validade < CURRENT_DATE THEN 'expirado'
        WHEN c.data_validade < CURRENT_DATE + INTERVAL '90 days' THEN 'expirando'
        ELSE 'valido'
    END                                         AS status_validade,

    -- Days until expiry
    CASE
        WHEN c.data_validade IS NOT NULL
        THEN c.data_validade - CURRENT_DATE
    END                                         AS dias_para_expirar,

    -- Duration of validity in days
    CASE
        WHEN c.data_validade IS NOT NULL
        THEN c.data_validade - c.data_emissao
    END                                         AS duracao_validade_dias,

    c.verificado,
    c.data_verificacao,

    -- Prestige level per certification type
    CASE c.tipo
        WHEN 'disney'   THEN 5
        WHEN 'nbcu'     THEN 5
        WHEN 'abvtex'   THEN 4
        WHEN 'gots'     THEN 4
        WHEN 'oeko_tex' THEN 4
        WHEN 'iso9001'  THEN 3
        WHEN 'bsci'     THEN 3
        WHEN 'wrap'     THEN 3
        ELSE 2
    END                                         AS prestigio_certificacao,

    -- Timestamps
    c.created_at,
    c.updated_at

FROM certificacoes c
WHERE c.ativo = TRUE
;
