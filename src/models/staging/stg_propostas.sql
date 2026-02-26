-- ============================================================================
-- stg_propostas — Staging model for workshop bids
-- ============================================================================

CREATE OR REPLACE VIEW stg_propostas AS
SELECT
    pr.id                                       AS proposta_id,
    pr.pedido_id,
    pr.oficina_id,

    ROUND(pr.valor_proposto, 2)                 AS valor_proposto,
    pr.prazo_proposto,
    pr.descricao,
    pr.condicoes,
    pr.status,
    pr.data_resposta,
    pr.motivo_recusa,

    -- Response time in hours from submission to response
    CASE
        WHEN pr.data_resposta IS NOT NULL
        THEN ROUND(EXTRACT(EPOCH FROM (pr.data_resposta - pr.created_at)) / 3600, 2)
    END                                         AS horas_ate_resposta,

    -- Time from order publication to proposal submission
    CASE
        WHEN p.data_publicacao IS NOT NULL
        THEN ROUND(EXTRACT(EPOCH FROM (pr.created_at - p.data_publicacao)) / 3600, 2)
    END                                         AS horas_apos_publicacao,

    -- Status flags
    pr.status = 'aceita'                        AS foi_aceita,
    pr.status = 'recusada'                      AS foi_recusada,
    pr.status IN ('expirada', 'retirada')       AS nao_respondida,

    -- Value vs order estimate
    CASE
        WHEN p.valor_estimado > 0
        THEN ROUND((pr.valor_proposto - p.valor_estimado) / p.valor_estimado * 100, 2)
    END                                         AS pct_vs_estimado,

    -- Price per piece
    CASE
        WHEN p.quantidade_total > 0
        THEN ROUND(pr.valor_proposto / p.quantidade_total, 4)
    END                                         AS preco_por_peca_proposto,

    -- Timestamps
    pr.created_at                               AS dt_envio,
    pr.updated_at                               AS dt_atualizacao

FROM propostas pr
JOIN pedidos p ON pr.pedido_id = p.id
WHERE p.deleted_at IS NULL
;
