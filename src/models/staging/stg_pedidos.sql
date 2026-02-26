-- ============================================================================
-- stg_pedidos — Staging model for production orders
-- ============================================================================

CREATE OR REPLACE VIEW stg_pedidos AS
SELECT
    id                                          AS pedido_id,
    codigo,
    empresa_id,
    oficina_id,
    categoria_id,

    TRIM(titulo)                                AS titulo,
    descricao,

    -- Quantities
    quantidade_total,
    COALESCE(unidade, 'peças')                  AS unidade,

    -- Financials
    ROUND(COALESCE(valor_estimado, 0), 2)       AS valor_estimado,
    ROUND(COALESCE(valor_final, 0), 2)          AS valor_final,
    moeda,

    -- Discount vs estimate
    CASE
        WHEN valor_estimado > 0 AND valor_final IS NOT NULL
        THEN ROUND((valor_final - valor_estimado) / valor_estimado * 100, 2)
    END                                         AS pct_variacao_valor,

    -- Price per piece
    CASE
        WHEN quantidade_total > 0 AND valor_final IS NOT NULL
        THEN ROUND(valor_final / quantidade_total, 4)
        WHEN quantidade_total > 0 AND valor_estimado IS NOT NULL
        THEN ROUND(valor_estimado / quantidade_total, 4)
    END                                         AS preco_por_peca,

    -- Timeline
    data_publicacao,
    data_limite_propostas,
    prazo_entrega,
    data_entrega_real,

    -- Delivery performance
    CASE
        WHEN data_entrega_real IS NOT NULL AND prazo_entrega IS NOT NULL
        THEN data_entrega_real - prazo_entrega
    END                                         AS dias_atraso_entrega,

    CASE
        WHEN data_entrega_real IS NOT NULL AND prazo_entrega IS NOT NULL
        THEN data_entrega_real <= prazo_entrega
        ELSE NULL
    END                                         AS entregue_no_prazo,

    -- Time to publish
    CASE
        WHEN data_publicacao IS NOT NULL
        THEN EXTRACT(EPOCH FROM (data_publicacao - created_at)) / 3600
    END::NUMERIC(10,2)                          AS horas_para_publicar,

    -- Status
    status,
    prioridade,

    -- Status groupings for funnel
    CASE
        WHEN status = 'rascunho'                    THEN 1
        WHEN status = 'publicado'                   THEN 2
        WHEN status = 'em_negociacao'               THEN 3
        WHEN status = 'confirmado'                  THEN 4
        WHEN status IN ('em_producao')              THEN 5
        WHEN status = 'controle_qualidade'          THEN 6
        WHEN status = 'entregue'                    THEN 7
        WHEN status = 'finalizado'                  THEN 8
        WHEN status = 'cancelado'                   THEN -1
        WHEN status = 'disputa'                     THEN -2
        ELSE 0
    END                                             AS status_ordem,

    -- Is matched (has oficina assigned)
    oficina_id IS NOT NULL                          AS foi_matched,

    -- Is completed successfully
    status = 'finalizado'                           AS foi_finalizado,
    status = 'cancelado'                            AS foi_cancelado,

    -- Timestamps
    created_at                                  AS dt_criacao,
    updated_at                                  AS dt_atualizacao,
    deleted_at                                  AS dt_exclusao,

    -- Calendar helpers
    DATE_TRUNC('month', created_at)             AS mes_criacao,
    DATE_TRUNC('week', created_at)              AS semana_criacao,
    EXTRACT(YEAR FROM created_at)::INTEGER      AS ano_criacao,
    EXTRACT(MONTH FROM created_at)::INTEGER     AS mes_num_criacao

FROM pedidos
WHERE deleted_at IS NULL
;
