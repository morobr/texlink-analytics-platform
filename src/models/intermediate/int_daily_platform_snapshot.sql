-- ============================================================================
-- int_daily_platform_snapshot — Daily aggregated platform metrics
-- Foundation for time-series KPI tracking
-- ============================================================================

CREATE OR REPLACE VIEW int_daily_platform_snapshot AS
WITH date_series AS (
    SELECT generate_series(
        (SELECT MIN(dt_criacao)::DATE FROM stg_pedidos),
        CURRENT_DATE,
        '1 day'::INTERVAL
    )::DATE AS dia
),
daily_pedidos AS (
    SELECT
        dt_criacao::DATE                        AS dia,
        COUNT(*)                                AS novos_pedidos,
        COUNT(*) FILTER (WHERE status = 'publicado' OR data_publicacao IS NOT NULL) AS pedidos_publicados,
        COUNT(*) FILTER (WHERE foi_matched)     AS pedidos_matched,
        COUNT(*) FILTER (WHERE foi_finalizado)  AS pedidos_finalizados,
        COUNT(*) FILTER (WHERE foi_cancelado)   AS pedidos_cancelados,
        COALESCE(SUM(valor_final) FILTER (WHERE foi_finalizado), 0) AS gmv_dia
    FROM stg_pedidos
    GROUP BY dt_criacao::DATE
),
daily_signups AS (
    SELECT
        dt_cadastro::DATE                       AS dia,
        COUNT(*) FILTER (WHERE tipo_entidade = 'empresa')  AS novas_empresas,
        COUNT(*) FILTER (WHERE tipo_entidade = 'oficina')  AS novas_oficinas
    FROM stg_usuarios
    WHERE is_owner
    GROUP BY dt_cadastro::DATE
),
daily_pagamentos AS (
    SELECT
        data_pagamento::DATE                    AS dia,
        COUNT(*)                                AS pagamentos_processados,
        SUM(valor_bruto)                        AS receita_bruta,
        SUM(taxa_plataforma)                    AS receita_plataforma,
        SUM(valor_liquido)                      AS pago_oficinas
    FROM stg_pagamentos
    WHERE foi_pago AND data_pagamento IS NOT NULL
    GROUP BY data_pagamento::DATE
),
daily_propostas AS (
    SELECT
        dt_envio::DATE                          AS dia,
        COUNT(*)                                AS propostas_enviadas,
        COUNT(*) FILTER (WHERE foi_aceita)      AS propostas_aceitas
    FROM stg_propostas
    GROUP BY dt_envio::DATE
),
daily_eventos AS (
    SELECT
        dia_evento::DATE                        AS dia,
        COUNT(*)                                AS total_eventos,
        COUNT(DISTINCT usuario_id)              AS usuarios_ativos,
        COUNT(DISTINCT session_id)              AS sessoes
    FROM stg_eventos_plataforma
    GROUP BY dia_evento::DATE
)
SELECT
    ds.dia,

    -- New activity
    COALESCE(dp.novos_pedidos, 0)               AS novos_pedidos,
    COALESCE(dp.pedidos_publicados, 0)          AS pedidos_publicados,
    COALESCE(dp.pedidos_matched, 0)             AS pedidos_matched,
    COALESCE(dp.pedidos_finalizados, 0)         AS pedidos_finalizados,
    COALESCE(dp.pedidos_cancelados, 0)          AS pedidos_cancelados,
    COALESCE(dp.gmv_dia, 0)                     AS gmv_dia,

    -- New users
    COALESCE(dsg.novas_empresas, 0)             AS novas_empresas,
    COALESCE(dsg.novas_oficinas, 0)             AS novas_oficinas,

    -- Payments
    COALESCE(dpg.pagamentos_processados, 0)     AS pagamentos_processados,
    COALESCE(dpg.receita_bruta, 0)              AS receita_bruta,
    COALESCE(dpg.receita_plataforma, 0)         AS receita_plataforma,
    COALESCE(dpg.pago_oficinas, 0)              AS pago_oficinas,

    -- Proposals
    COALESCE(dpr.propostas_enviadas, 0)         AS propostas_enviadas,
    COALESCE(dpr.propostas_aceitas, 0)          AS propostas_aceitas,

    -- Engagement
    COALESCE(de.total_eventos, 0)               AS total_eventos,
    COALESCE(de.usuarios_ativos, 0)             AS usuarios_ativos,
    COALESCE(de.sessoes, 0)                     AS sessoes,

    -- 7-day rolling metrics
    SUM(COALESCE(dp.gmv_dia, 0)) OVER (
        ORDER BY ds.dia ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )                                           AS gmv_7d,
    SUM(COALESCE(dp.pedidos_finalizados, 0)) OVER (
        ORDER BY ds.dia ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )                                           AS pedidos_finalizados_7d,

    -- Calendar
    EXTRACT(DOW FROM ds.dia)::INTEGER           AS dia_semana,
    EXTRACT(WEEK FROM ds.dia)::INTEGER          AS semana_ano,
    DATE_TRUNC('month', ds.dia)                 AS mes,
    EXTRACT(YEAR FROM ds.dia)::INTEGER          AS ano

FROM date_series ds
LEFT JOIN daily_pedidos dp      ON ds.dia = dp.dia
LEFT JOIN daily_signups dsg     ON ds.dia = dsg.dia
LEFT JOIN daily_pagamentos dpg  ON ds.dia = dpg.dia
LEFT JOIN daily_propostas dpr   ON ds.dia = dpr.dia
LEFT JOIN daily_eventos de      ON ds.dia = de.dia
;
