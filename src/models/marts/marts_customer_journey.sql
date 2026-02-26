-- ============================================================================
-- marts_customer_journey — Full funnel analysis
-- Signup → Activation → Match → Conversion → Retention
-- ============================================================================

CREATE OR REPLACE VIEW marts_customer_journey AS
WITH funnel_cohort AS (
    SELECT
        cohort_mes,
        COUNT(DISTINCT empresa_id)                              AS n_registered,
        COUNT(DISTINCT empresa_id) FILTER (WHERE stage_num >= 2) AS n_activated,
        COUNT(DISTINCT empresa_id) FILTER (WHERE stage_num >= 3) AS n_matched,
        COUNT(DISTINCT empresa_id) FILTER (WHERE stage_num >= 4) AS n_converted,
        COUNT(DISTINCT empresa_id) FILTER (WHERE stage_num >= 5) AS n_retained,

        -- Median time-between-stages
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dias_signup_para_ativacao)   AS p50_dias_ativacao,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dias_ativacao_para_match)    AS p50_dias_match,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dias_match_para_conversao)   AS p50_dias_conversao,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dias_conversao_para_retencao) AS p50_dias_retencao,

        -- Mean time
        ROUND(AVG(dias_signup_para_ativacao), 1)               AS avg_dias_ativacao,
        ROUND(AVG(dias_ativacao_para_match), 1)                AS avg_dias_match,
        ROUND(AVG(dias_match_para_conversao), 1)               AS avg_dias_conversao

    FROM int_funnel_stages
    GROUP BY cohort_mes
)
SELECT
    fc.cohort_mes,
    TO_CHAR(fc.cohort_mes, 'YYYY-MM')           AS cohort_label,

    -- Absolute counts per stage
    fc.n_registered,
    fc.n_activated,
    fc.n_matched,
    fc.n_converted,
    fc.n_retained,

    -- Conversion rates (relative to registered)
    ROUND(fc.n_activated::NUMERIC / NULLIF(fc.n_registered, 0) * 100, 2)  AS pct_ativacao,
    ROUND(fc.n_matched::NUMERIC   / NULLIF(fc.n_registered, 0) * 100, 2)  AS pct_match,
    ROUND(fc.n_converted::NUMERIC / NULLIF(fc.n_registered, 0) * 100, 2)  AS pct_conversao,
    ROUND(fc.n_retained::NUMERIC  / NULLIF(fc.n_registered, 0) * 100, 2)  AS pct_retencao,

    -- Step conversion rates
    ROUND(fc.n_activated::NUMERIC / NULLIF(fc.n_registered, 0) * 100, 2)  AS step_signup_to_activation,
    ROUND(fc.n_matched::NUMERIC   / NULLIF(fc.n_activated, 0) * 100, 2)   AS step_activation_to_match,
    ROUND(fc.n_converted::NUMERIC / NULLIF(fc.n_matched, 0) * 100, 2)     AS step_match_to_conversion,
    ROUND(fc.n_retained::NUMERIC  / NULLIF(fc.n_converted, 0) * 100, 2)   AS step_conversion_to_retention,

    -- Drop-off counts
    fc.n_registered - fc.n_activated           AS dropoff_no_signup,
    fc.n_activated  - fc.n_matched             AS dropoff_apos_ativacao,
    fc.n_matched    - fc.n_converted           AS dropoff_apos_match,
    fc.n_converted  - fc.n_retained            AS dropoff_apos_conversao,

    -- Time-to-stage medians
    fc.p50_dias_ativacao,
    fc.p50_dias_match,
    fc.p50_dias_conversao,
    fc.p50_dias_retencao,
    fc.avg_dias_ativacao,
    fc.avg_dias_match,
    fc.avg_dias_conversao

FROM funnel_cohort fc
ORDER BY fc.cohort_mes
;
