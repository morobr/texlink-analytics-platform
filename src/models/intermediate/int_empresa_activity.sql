-- ============================================================================
-- int_empresa_activity — Brand engagement and ordering metrics
-- ============================================================================

CREATE OR REPLACE VIEW int_empresa_activity AS
WITH order_history AS (
    SELECT
        empresa_id,
        COUNT(*)                                                AS total_pedidos,
        COUNT(*) FILTER (WHERE foi_finalizado)                 AS pedidos_finalizados,
        COUNT(*) FILTER (WHERE foi_cancelado)                  AS pedidos_cancelados,
        COUNT(*) FILTER (WHERE foi_matched)                    AS pedidos_matched,
        COALESCE(SUM(valor_final) FILTER (WHERE foi_finalizado), 0) AS gmv_total,
        COALESCE(AVG(valor_final) FILTER (WHERE foi_finalizado), 0) AS aov,
        COALESCE(SUM(quantidade_total), 0)                     AS total_pecas_pedidas,
        MIN(dt_criacao)                                        AS primeiro_pedido,
        MAX(dt_criacao)                                        AS ultimo_pedido,
        COUNT(DISTINCT DATE_TRUNC('month', dt_criacao))        AS meses_com_pedido
    FROM stg_pedidos
    GROUP BY empresa_id
),
repeat_orders AS (
    SELECT
        empresa_id,
        COUNT(*) FILTER (WHERE pedido_rank > 1)                AS pedidos_repetidos
    FROM (
        SELECT
            empresa_id,
            ROW_NUMBER() OVER (PARTITION BY empresa_id ORDER BY dt_criacao) AS pedido_rank
        FROM stg_pedidos
        WHERE NOT foi_cancelado
    ) ranked
    GROUP BY empresa_id
),
event_activity AS (
    SELECT
        u.empresa_id,
        COUNT(e.evento_id)                                     AS total_eventos,
        COUNT(DISTINCT e.dia_evento)                           AS dias_ativos,
        MAX(e.dt_evento)                                       AS ultimo_evento,
        COUNT(*) FILTER (WHERE e.tipo = 'search_performed')    AS total_buscas,
        COUNT(*) FILTER (WHERE e.tipo = 'oficina_viewed')      AS oficinas_visualizadas
    FROM stg_eventos_plataforma e
    JOIN stg_usuarios u ON e.usuario_id = u.usuario_id
    WHERE u.empresa_id IS NOT NULL
    GROUP BY u.empresa_id
)
SELECT
    e.empresa_id,
    e.nome_fantasia,
    e.estado,
    e.segmento,
    e.porte,
    e.dt_cadastro,
    e.status_cadastro,

    -- Order metrics
    COALESCE(oh.total_pedidos, 0)               AS total_pedidos,
    COALESCE(oh.pedidos_finalizados, 0)         AS pedidos_finalizados,
    COALESCE(oh.pedidos_cancelados, 0)          AS pedidos_cancelados,
    COALESCE(oh.pedidos_matched, 0)             AS pedidos_matched,
    ROUND(COALESCE(oh.gmv_total, 0), 2)         AS gmv_total,
    ROUND(COALESCE(oh.aov, 0), 2)              AS aov,
    COALESCE(oh.total_pecas_pedidas, 0)         AS total_pecas_pedidas,
    oh.primeiro_pedido,
    oh.ultimo_pedido,
    COALESCE(oh.meses_com_pedido, 0)            AS meses_com_pedido,

    -- Match rate
    CASE
        WHEN COALESCE(oh.total_pedidos, 0) > 0
        THEN ROUND(oh.pedidos_matched::NUMERIC / oh.total_pedidos * 100, 2)
    END                                         AS match_rate_pct,

    -- Repeat purchase
    COALESCE(rp.pedidos_repetidos, 0) > 0       AS e_cliente_recorrente,
    COALESCE(rp.pedidos_repetidos, 0)           AS pedidos_repetidos,

    -- Order frequency (orders per month with orders)
    CASE
        WHEN COALESCE(oh.meses_com_pedido, 0) > 0
        THEN ROUND(oh.total_pedidos::NUMERIC / oh.meses_com_pedido, 2)
    END                                         AS pedidos_por_mes_ativo,

    -- Recency (days since last order)
    CASE
        WHEN oh.ultimo_pedido IS NOT NULL
        THEN EXTRACT(EPOCH FROM (NOW() - oh.ultimo_pedido)) / 86400
    END::INTEGER                                AS dias_desde_ultimo_pedido,

    -- Lifecycle stage
    CASE
        WHEN COALESCE(oh.total_pedidos, 0) = 0             THEN 'nunca_pediu'
        WHEN oh.ultimo_pedido >= NOW() - INTERVAL '30 days' THEN 'ativo'
        WHEN oh.ultimo_pedido >= NOW() - INTERVAL '90 days' THEN 'em_risco'
        ELSE 'churned'
    END                                         AS lifecycle_stage,

    -- Platform engagement
    COALESCE(ea.total_eventos, 0)               AS total_eventos,
    COALESCE(ea.dias_ativos, 0)                 AS dias_ativos_plataforma,
    COALESCE(ea.total_buscas, 0)               AS total_buscas,
    COALESCE(ea.oficinas_visualizadas, 0)       AS oficinas_visualizadas,
    ea.ultimo_evento

FROM stg_empresas e
LEFT JOIN order_history oh  ON e.empresa_id = oh.empresa_id
LEFT JOIN repeat_orders rp  ON e.empresa_id = rp.empresa_id
LEFT JOIN event_activity ea ON e.empresa_id = ea.empresa_id
;
