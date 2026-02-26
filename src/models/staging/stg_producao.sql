-- ============================================================================
-- stg_producao — Staging model for production tracking
-- ============================================================================

CREATE OR REPLACE VIEW stg_producao AS
SELECT
    pr.id                                       AS producao_id,
    pr.pedido_id,
    pr.oficina_id,

    pr.status,
    ROUND(pr.percentual_concluido, 2)           AS pct_concluido,

    -- Quantities
    COALESCE(pr.quantidade_produzida, 0)        AS qtd_produzida,
    COALESCE(pr.quantidade_aprovada, 0)         AS qtd_aprovada,
    COALESCE(pr.quantidade_rejeitada, 0)        AS qtd_rejeitada,

    -- Quality rate
    CASE
        WHEN pr.quantidade_produzida > 0
        THEN ROUND(pr.quantidade_aprovada::NUMERIC / pr.quantidade_produzida * 100, 2)
        ELSE NULL
    END                                         AS taxa_aprovacao_pct,

    -- Rejection rate
    CASE
        WHEN pr.quantidade_produzida > 0
        THEN ROUND(pr.quantidade_rejeitada::NUMERIC / pr.quantidade_produzida * 100, 2)
        ELSE NULL
    END                                         AS taxa_rejeicao_pct,

    -- Timeline
    pr.data_inicio,
    pr.data_previsao,
    pr.data_conclusao,

    -- Production duration in days
    CASE
        WHEN pr.data_conclusao IS NOT NULL AND pr.data_inicio IS NOT NULL
        THEN EXTRACT(EPOCH FROM (pr.data_conclusao - pr.data_inicio)) / 86400
    END::INTEGER                                AS dias_producao,

    -- On-time completion
    CASE
        WHEN pr.data_conclusao IS NOT NULL AND pr.data_previsao IS NOT NULL
        THEN pr.data_conclusao::DATE <= pr.data_previsao
        ELSE NULL
    END                                         AS concluido_no_prazo,

    pr.observacoes_qualidade,

    -- Timestamps
    pr.created_at                               AS dt_inicio_registro,
    pr.updated_at                               AS dt_atualizacao

FROM producao pr
;
