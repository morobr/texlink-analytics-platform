-- ============================================================================
-- marts_platform_kpis — Executive platform KPI dashboard
-- Monthly granularity: GMV, take rate, liquidity, growth, active users
-- ============================================================================

CREATE OR REPLACE VIEW marts_platform_kpis AS
WITH monthly_base AS (
    SELECT
        DATE_TRUNC('month', dia)                AS mes,
        SUM(gmv_dia)                            AS gmv,
        SUM(receita_plataforma)                 AS receita_plataforma,
        SUM(novos_pedidos)                      AS novos_pedidos,
        SUM(pedidos_publicados)                 AS pedidos_publicados,
        SUM(pedidos_matched)                    AS pedidos_matched,
        SUM(pedidos_finalizados)                AS pedidos_finalizados,
        SUM(pedidos_cancelados)                 AS pedidos_cancelados,
        SUM(propostas_enviadas)                 AS propostas_enviadas,
        SUM(novas_empresas)                     AS novas_empresas,
        SUM(novas_oficinas)                     AS novas_oficinas,
        AVG(NULLIF(usuarios_ativos, 0))         AS usuarios_ativos_media
    FROM int_daily_platform_snapshot
    WHERE dia <= CURRENT_DATE
    GROUP BY DATE_TRUNC('month', dia)
),
monthly_actives AS (
    -- Count distinct active entities per month
    SELECT
        DATE_TRUNC('month', dt_criacao)         AS mes,
        COUNT(DISTINCT empresa_id)              AS empresas_com_pedido,
        COUNT(DISTINCT oficina_id) FILTER (WHERE foi_matched) AS oficinas_com_pedido
    FROM stg_pedidos
    GROUP BY DATE_TRUNC('month', dt_criacao)
),
total_registered AS (
    SELECT
        DATE_TRUNC('month', dt_cadastro)        AS mes,
        COUNT(*) FILTER (WHERE tipo_entidade = 'empresa' AND is_owner) AS empresas_cadastradas_mes,
        COUNT(*) FILTER (WHERE tipo_entidade = 'oficina' AND is_owner) AS oficinas_cadastradas_mes
    FROM stg_usuarios
    GROUP BY DATE_TRUNC('month', dt_cadastro)
)
SELECT
    mb.mes,
    TO_CHAR(mb.mes, 'YYYY-MM')                 AS mes_label,

    -- Volume
    ROUND(mb.gmv, 2)                            AS gmv,
    ROUND(mb.receita_plataforma, 2)             AS receita_plataforma,

    -- Take rate
    CASE
        WHEN mb.gmv > 0
        THEN ROUND(mb.receita_plataforma / mb.gmv * 100, 2)
    END                                         AS take_rate_pct,

    -- Orders
    mb.novos_pedidos,
    mb.pedidos_publicados,
    mb.pedidos_matched,
    mb.pedidos_finalizados,
    mb.pedidos_cancelados,

    -- Liquidity: % of published orders that get ≥1 proposal
    CASE
        WHEN mb.pedidos_publicados > 0
        THEN ROUND(mb.pedidos_matched::NUMERIC / mb.pedidos_publicados * 100, 2)
    END                                         AS liquidez_pct,

    -- Match rate
    CASE
        WHEN mb.pedidos_publicados > 0
        THEN ROUND(mb.pedidos_matched::NUMERIC / mb.pedidos_publicados * 100, 2)
    END                                         AS match_rate_pct,

    -- Completion rate
    CASE
        WHEN mb.pedidos_matched > 0
        THEN ROUND(mb.pedidos_finalizados::NUMERIC / mb.pedidos_matched * 100, 2)
    END                                         AS completion_rate_pct,

    -- Proposals
    mb.propostas_enviadas,
    CASE
        WHEN mb.pedidos_publicados > 0
        THEN ROUND(mb.propostas_enviadas::NUMERIC / mb.pedidos_publicados, 2)
    END                                         AS propostas_por_pedido,

    -- New users
    mb.novas_empresas,
    mb.novas_oficinas,

    -- Active base
    COALESCE(ma.empresas_com_pedido, 0)         AS empresas_ativas,
    COALESCE(ma.oficinas_com_pedido, 0)         AS oficinas_ativas,

    -- GMV per order
    CASE
        WHEN mb.pedidos_finalizados > 0
        THEN ROUND(mb.gmv / mb.pedidos_finalizados, 2)
    END                                         AS gmv_por_pedido,

    -- Month-over-month growth
    LAG(mb.gmv) OVER (ORDER BY mb.mes)          AS gmv_mes_anterior,
    CASE
        WHEN LAG(mb.gmv) OVER (ORDER BY mb.mes) > 0
        THEN ROUND(
            (mb.gmv - LAG(mb.gmv) OVER (ORDER BY mb.mes)) /
            LAG(mb.gmv) OVER (ORDER BY mb.mes) * 100, 2
        )
    END                                         AS gmv_growth_mom_pct,

    LAG(mb.pedidos_finalizados) OVER (ORDER BY mb.mes) AS pedidos_mes_anterior,
    CASE
        WHEN LAG(mb.pedidos_finalizados) OVER (ORDER BY mb.mes) > 0
        THEN ROUND(
            (mb.pedidos_finalizados - LAG(mb.pedidos_finalizados) OVER (ORDER BY mb.mes))::NUMERIC /
            LAG(mb.pedidos_finalizados) OVER (ORDER BY mb.mes) * 100, 2
        )
    END                                         AS orders_growth_mom_pct,

    -- Cumulative GMV
    SUM(mb.gmv) OVER (ORDER BY mb.mes)          AS gmv_acumulado,

    -- Is current month (partial)
    mb.mes = DATE_TRUNC('month', CURRENT_DATE)  AS mes_atual

FROM monthly_base mb
LEFT JOIN monthly_actives ma ON mb.mes = ma.mes
ORDER BY mb.mes
;
