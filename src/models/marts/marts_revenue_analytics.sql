-- ============================================================================
-- marts_revenue_analytics — Revenue decomposition and unit economics
-- ============================================================================

CREATE OR REPLACE VIEW marts_revenue_analytics AS
WITH monthly_rev AS (
    SELECT
        DATE_TRUNC('month', COALESCE(data_pagamento, dt_criacao)) AS mes,
        metodo,
        COUNT(*)                                                AS n_pagamentos,
        SUM(valor_bruto)                                        AS gmv,
        SUM(taxa_plataforma)                                    AS receita_bruta,
        SUM(valor_liquido)                                      AS pago_oficinas,
        AVG(pct_taxa * 100)                                     AS taxa_media_pct,
        SUM(valor_bruto) FILTER (WHERE metodo = 'pix')         AS gmv_pix,
        SUM(valor_bruto) FILTER (WHERE metodo = 'boleto')      AS gmv_boleto,
        SUM(valor_bruto) FILTER (WHERE metodo = 'transferencia') AS gmv_transferencia
    FROM stg_pagamentos
    WHERE foi_pago
    GROUP BY DATE_TRUNC('month', COALESCE(data_pagamento, dt_criacao)), metodo
),
monthly_agg AS (
    SELECT
        mes,
        SUM(n_pagamentos)       AS n_pagamentos,
        SUM(gmv)                AS gmv,
        SUM(receita_bruta)      AS receita_bruta,
        SUM(pago_oficinas)      AS pago_oficinas,
        AVG(taxa_media_pct)     AS taxa_media_pct,
        MAX(gmv_pix)            AS gmv_pix,
        MAX(gmv_boleto)         AS gmv_boleto,
        MAX(gmv_transferencia)  AS gmv_transferencia
    FROM monthly_rev
    GROUP BY mes
),
unit_econ AS (
    -- Cost per acquisition proxies (new empresa per month)
    SELECT
        DATE_TRUNC('month', dt_cadastro)        AS mes,
        COUNT(*) FILTER (WHERE tipo_entidade = 'empresa' AND is_owner) AS new_empresas
    FROM stg_usuarios
    GROUP BY DATE_TRUNC('month', dt_cadastro)
)
SELECT
    ma.mes,
    TO_CHAR(ma.mes, 'YYYY-MM')                  AS mes_label,

    -- Revenue
    ROUND(ma.gmv, 2)                            AS gmv,
    ROUND(ma.receita_bruta, 2)                  AS receita_plataforma,
    ROUND(ma.pago_oficinas, 2)                  AS pago_oficinas,
    ROUND(ma.taxa_media_pct, 2)                 AS take_rate_real_pct,

    -- Transaction metrics
    ma.n_pagamentos,
    ROUND(ma.gmv / NULLIF(ma.n_pagamentos, 0), 2) AS ticket_medio,

    -- Payment method mix
    ROUND(COALESCE(ma.gmv_pix, 0) / NULLIF(ma.gmv, 0) * 100, 2)          AS pct_pix,
    ROUND(COALESCE(ma.gmv_boleto, 0) / NULLIF(ma.gmv, 0) * 100, 2)       AS pct_boleto,
    ROUND(COALESCE(ma.gmv_transferencia, 0) / NULLIF(ma.gmv, 0) * 100, 2) AS pct_transferencia,

    -- Unit economics
    COALESCE(ue.new_empresas, 0)                AS new_empresas,
    CASE
        WHEN COALESCE(ue.new_empresas, 0) > 0
        THEN ROUND(ma.receita_bruta / ue.new_empresas, 2)
    END                                         AS receita_por_nova_empresa,

    -- MoM growth
    LAG(ma.gmv) OVER (ORDER BY ma.mes)          AS gmv_mes_anterior,
    ROUND(
        (ma.gmv - LAG(ma.gmv) OVER (ORDER BY ma.mes)) /
        NULLIF(LAG(ma.gmv) OVER (ORDER BY ma.mes), 0) * 100, 2
    )                                           AS gmv_growth_pct,

    ROUND(
        (ma.receita_bruta - LAG(ma.receita_bruta) OVER (ORDER BY ma.mes)) /
        NULLIF(LAG(ma.receita_bruta) OVER (ORDER BY ma.mes), 0) * 100, 2
    )                                           AS receita_growth_pct,

    -- Cumulative
    SUM(ma.gmv) OVER (ORDER BY ma.mes)          AS gmv_acumulado,
    SUM(ma.receita_bruta) OVER (ORDER BY ma.mes) AS receita_acumulada

FROM monthly_agg ma
LEFT JOIN unit_econ ue ON ma.mes = ue.mes
ORDER BY ma.mes
;
