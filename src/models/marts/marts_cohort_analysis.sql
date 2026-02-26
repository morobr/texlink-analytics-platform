-- ============================================================================
-- marts_cohort_analysis — Monthly retention cohorts
-- Shows % of cohort that placed an order in each subsequent month
-- ============================================================================

CREATE OR REPLACE VIEW marts_cohort_analysis AS
WITH cohort_base AS (
    -- Each empresa's signup cohort
    SELECT
        e.empresa_id,
        DATE_TRUNC('month', e.dt_cadastro)      AS cohort_mes
    FROM stg_empresas e
    WHERE e.dt_cadastro IS NOT NULL
),
orders_by_month AS (
    -- When each empresa placed orders
    SELECT
        p.empresa_id,
        DATE_TRUNC('month', p.dt_criacao)       AS order_mes
    FROM stg_pedidos p
    WHERE NOT p.foi_cancelado
    GROUP BY p.empresa_id, DATE_TRUNC('month', p.dt_criacao)
),
cohort_orders AS (
    SELECT
        cb.empresa_id,
        cb.cohort_mes,
        ob.order_mes,
        -- Months since cohort signup
        EXTRACT(YEAR FROM AGE(ob.order_mes, cb.cohort_mes)) * 12 +
        EXTRACT(MONTH FROM AGE(ob.order_mes, cb.cohort_mes)) AS months_since_signup
    FROM cohort_base cb
    LEFT JOIN orders_by_month ob ON cb.empresa_id = ob.empresa_id
        AND ob.order_mes >= cb.cohort_mes
),
cohort_sizes AS (
    SELECT
        cohort_mes,
        COUNT(DISTINCT empresa_id)              AS cohort_size
    FROM cohort_base
    GROUP BY cohort_mes
)
SELECT
    co.cohort_mes,
    TO_CHAR(co.cohort_mes, 'YYYY-MM')           AS cohort_label,
    cs.cohort_size,
    co.months_since_signup                      AS mes_n,

    -- Active count in period N
    COUNT(DISTINCT co.empresa_id)               AS n_ativos,

    -- Retention rate
    ROUND(
        COUNT(DISTINCT co.empresa_id)::NUMERIC / cs.cohort_size * 100, 2
    )                                           AS retention_rate_pct,

    -- Revenue from cohort in period N
    ROUND(
        COALESCE(SUM(p.valor_final), 0), 2
    )                                           AS receita_cohort

FROM cohort_orders co
JOIN cohort_sizes cs ON co.cohort_mes = cs.cohort_mes
LEFT JOIN stg_pedidos p ON co.empresa_id = p.empresa_id
    AND DATE_TRUNC('month', p.dt_criacao) = co.order_mes
    AND NOT p.foi_cancelado
WHERE co.order_mes IS NOT NULL
GROUP BY co.cohort_mes, cs.cohort_size, co.months_since_signup
ORDER BY co.cohort_mes, co.months_since_signup
;
