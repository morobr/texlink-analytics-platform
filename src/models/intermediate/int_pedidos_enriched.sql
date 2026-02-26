-- ============================================================================
-- int_pedidos_enriched — Orders with full context
-- Joins pedidos with empresa, oficina, categoria, and payment details
-- ============================================================================

CREATE OR REPLACE VIEW int_pedidos_enriched AS
SELECT
    -- Core order
    p.pedido_id,
    p.codigo,
    p.status,
    p.status_ordem,
    p.foi_matched,
    p.foi_finalizado,
    p.foi_cancelado,

    -- Empresa (demand side)
    e.empresa_id,
    e.nome_fantasia                             AS empresa_nome,
    e.estado                                    AS empresa_estado,
    e.cidade                                    AS empresa_cidade,
    e.porte                                     AS empresa_porte,
    e.segmento                                  AS empresa_segmento,

    -- Oficina (supply side — may be NULL for unmatched orders)
    o.oficina_id,
    o.nome_fantasia                             AS oficina_nome,
    o.estado                                    AS oficina_estado,
    o.cidade                                    AS oficina_cidade,
    o.tier                                      AS oficina_tier,
    o.score_medio                               AS oficina_score,
    o.capacidade_mensal_pecas,

    -- Category
    c.nome                                      AS categoria_nome,
    c_parent.nome                               AS categoria_pai,

    -- Financials
    p.quantidade_total,
    p.valor_estimado,
    p.valor_final,
    p.preco_por_peca,
    p.pct_variacao_valor,

    -- Payment details (from finalized orders)
    pg.valor_bruto                              AS pagamento_valor_bruto,
    pg.taxa_plataforma,
    pg.valor_liquido                            AS pagamento_liquido,
    pg.pct_taxa                                 AS taxa_plataforma_pct,
    pg.metodo                                   AS metodo_pagamento,
    pg.foi_pago,

    -- Timeline
    p.dt_criacao,
    p.data_publicacao,
    p.data_limite_propostas,
    p.prazo_entrega,
    p.data_entrega_real,
    p.horas_para_publicar,
    p.dias_atraso_entrega,
    p.entregue_no_prazo,

    -- Proposal metrics
    prop_summary.total_propostas,
    prop_summary.proposta_aceita_valor,
    prop_summary.horas_primeira_proposta,
    prop_summary.horas_match,

    -- Calendar
    p.mes_criacao,
    p.semana_criacao,
    p.ano_criacao,
    p.mes_num_criacao,

    -- Cross-state match flag
    CASE
        WHEN e.estado IS NOT NULL AND o.estado IS NOT NULL
        THEN e.estado != o.estado
        ELSE NULL
    END                                         AS match_interestadual

FROM stg_pedidos p
JOIN stg_empresas e  ON p.empresa_id = e.empresa_id
LEFT JOIN stg_oficinas o ON p.oficina_id = o.oficina_id
LEFT JOIN categorias_produto c ON p.categoria_id = c.id
LEFT JOIN categorias_produto c_parent ON c.parent_id = c_parent.id
LEFT JOIN stg_pagamentos pg ON p.pedido_id = pg.pedido_id AND pg.foi_pago

-- Proposal summary subquery
LEFT JOIN (
    SELECT
        pedido_id,
        COUNT(*)                                AS total_propostas,
        MIN(CASE WHEN foi_aceita THEN valor_proposto END) AS proposta_aceita_valor,
        MIN(horas_apos_publicacao)              AS horas_primeira_proposta,
        MIN(CASE WHEN foi_aceita THEN horas_apos_publicacao END) AS horas_match
    FROM stg_propostas
    GROUP BY pedido_id
) prop_summary ON p.pedido_id = prop_summary.pedido_id
;
