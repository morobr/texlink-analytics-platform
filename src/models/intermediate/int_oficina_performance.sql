-- ============================================================================
-- int_oficina_performance — Aggregated workshop performance metrics
-- ============================================================================

CREATE OR REPLACE VIEW int_oficina_performance AS
WITH order_metrics AS (
    SELECT
        o.oficina_id,
        COUNT(*)                                                AS total_pedidos,
        COUNT(*) FILTER (WHERE p.foi_finalizado)               AS pedidos_finalizados,
        COUNT(*) FILTER (WHERE p.foi_cancelado)                AS pedidos_cancelados,
        COALESCE(SUM(p.valor_final) FILTER (WHERE p.foi_finalizado), 0) AS gmv_total,
        COALESCE(AVG(p.valor_final) FILTER (WHERE p.foi_finalizado), 0) AS ticket_medio,
        COALESCE(SUM(p.quantidade_total), 0)                   AS total_pecas_produzidas,
        MIN(p.dt_criacao)                                      AS primeiro_pedido,
        MAX(p.dt_criacao)                                      AS ultimo_pedido
    FROM stg_oficinas o
    LEFT JOIN stg_pedidos p ON o.oficina_id = p.oficina_id
    GROUP BY o.oficina_id
),
proposal_metrics AS (
    SELECT
        pr.oficina_id,
        COUNT(*)                                                AS total_propostas_enviadas,
        COUNT(*) FILTER (WHERE pr.foi_aceita)                  AS propostas_aceitas,
        ROUND(
            COUNT(*) FILTER (WHERE pr.foi_aceita)::NUMERIC /
            NULLIF(COUNT(*), 0) * 100, 2
        )                                                       AS win_rate_pct,
        ROUND(AVG(pr.horas_apos_publicacao), 2)                AS tempo_medio_resposta_h,
        ROUND(MIN(pr.horas_apos_publicacao), 2)                AS tempo_min_resposta_h
    FROM stg_propostas pr
    GROUP BY pr.oficina_id
),
production_metrics AS (
    SELECT
        pr.oficina_id,
        ROUND(AVG(pr.taxa_aprovacao_pct), 2)                   AS taxa_aprovacao_media_pct,
        ROUND(AVG(pr.taxa_rejeicao_pct), 2)                    AS taxa_rejeicao_media_pct,
        COUNT(*) FILTER (WHERE pr.concluido_no_prazo)          AS producoes_no_prazo,
        COUNT(*)                                               AS total_producoes,
        ROUND(
            COUNT(*) FILTER (WHERE pr.concluido_no_prazo)::NUMERIC /
            NULLIF(COUNT(*), 0) * 100, 2
        )                                                       AS pct_no_prazo,
        ROUND(AVG(pr.dias_producao), 1)                        AS tempo_medio_producao_dias
    FROM stg_producao pr
    GROUP BY pr.oficina_id
),
avaliacao_metrics AS (
    SELECT
        a.avaliado_oficina_id                                   AS oficina_id,
        COUNT(*)                                                AS total_avaliacoes_recebidas,
        ROUND(AVG(a.nota_geral), 2)                            AS nota_geral_media,
        ROUND(AVG(a.nota_qualidade), 2)                        AS nota_qualidade_media,
        ROUND(AVG(a.nota_pontualidade), 2)                     AS nota_pontualidade_media,
        ROUND(AVG(a.nota_comunicacao), 2)                      AS nota_comunicacao_media,
        COUNT(*) FILTER (WHERE a.sentimento = 'positivo')      AS avaliacoes_positivas,
        COUNT(*) FILTER (WHERE a.sentimento = 'negativo')      AS avaliacoes_negativas
    FROM stg_avaliacoes a
    WHERE a.avaliado_oficina_id IS NOT NULL
    GROUP BY a.avaliado_oficina_id
),
cert_metrics AS (
    SELECT
        oficina_id,
        COUNT(*)                                                AS total_certificacoes,
        SUM(prestigio_certificacao)                            AS score_certificacoes,
        BOOL_OR(tipo = 'abvtex')                               AS tem_abvtex,
        BOOL_OR(tipo IN ('nbcu', 'disney'))                    AS tem_certificacao_premium
    FROM stg_certificacoes
    WHERE status_validade IN ('valido', 'expirando')
    GROUP BY oficina_id
)
SELECT
    o.oficina_id,
    o.nome_fantasia,
    o.estado,
    o.cidade,
    o.tier,
    o.capacidade_mensal_pecas,
    o.num_especialidades,

    -- Order performance
    COALESCE(om.total_pedidos, 0)               AS total_pedidos,
    COALESCE(om.pedidos_finalizados, 0)         AS pedidos_finalizados,
    COALESCE(om.pedidos_cancelados, 0)          AS pedidos_cancelados,
    CASE
        WHEN COALESCE(om.total_pedidos, 0) > 0
        THEN ROUND(om.pedidos_finalizados::NUMERIC / om.total_pedidos * 100, 2)
    END                                         AS taxa_conclusao_pct,
    ROUND(COALESCE(om.gmv_total, 0), 2)         AS gmv_total,
    ROUND(COALESCE(om.ticket_medio, 0), 2)      AS ticket_medio,
    COALESCE(om.total_pecas_produzidas, 0)      AS total_pecas_produzidas,
    om.primeiro_pedido,
    om.ultimo_pedido,

    -- Proposal / matching
    COALESCE(pm.total_propostas_enviadas, 0)    AS total_propostas_enviadas,
    COALESCE(pm.propostas_aceitas, 0)           AS propostas_aceitas,
    COALESCE(pm.win_rate_pct, 0)                AS win_rate_pct,
    COALESCE(pm.tempo_medio_resposta_h, 0)      AS tempo_medio_resposta_h,

    -- Production quality
    COALESCE(prom.taxa_aprovacao_media_pct, 0)  AS taxa_aprovacao_media_pct,
    COALESCE(prom.pct_no_prazo, 0)              AS pct_entrega_no_prazo,
    COALESCE(prom.tempo_medio_producao_dias, 0) AS tempo_medio_producao_dias,

    -- Ratings
    COALESCE(am.total_avaliacoes_recebidas, 0)  AS total_avaliacoes,
    COALESCE(am.nota_geral_media, 0)            AS nota_geral_media,
    COALESCE(am.nota_qualidade_media, 0)        AS nota_qualidade_media,
    COALESCE(am.nota_pontualidade_media, 0)     AS nota_pontualidade_media,
    COALESCE(am.nota_comunicacao_media, 0)      AS nota_comunicacao_media,

    -- Certifications
    COALESCE(cm.total_certificacoes, 0)         AS total_certificacoes,
    COALESCE(cm.score_certificacoes, 0)         AS score_certificacoes,
    COALESCE(cm.tem_abvtex, FALSE)              AS tem_abvtex,
    COALESCE(cm.tem_certificacao_premium, FALSE) AS tem_cert_premium,

    -- Capacity utilization
    CASE
        WHEN o.capacidade_mensal_pecas > 0
        THEN ROUND(
            COALESCE(om.total_pecas_produzidas, 0)::NUMERIC /
            (o.capacidade_mensal_pecas * 18) * 100, 2  -- 18 months of history
        )
    END                                         AS taxa_utilizacao_capacidade_pct,

    -- Is currently active (had pedido in last 60 days)
    om.ultimo_pedido >= NOW() - INTERVAL '60 days' AS ativo_recente

FROM stg_oficinas o
LEFT JOIN order_metrics om      ON o.oficina_id = om.oficina_id
LEFT JOIN proposal_metrics pm   ON o.oficina_id = pm.oficina_id
LEFT JOIN production_metrics prom ON o.oficina_id = prom.oficina_id
LEFT JOIN avaliacao_metrics am  ON o.oficina_id = am.oficina_id
LEFT JOIN cert_metrics cm       ON o.oficina_id = cm.oficina_id
;
