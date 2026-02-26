-- ============================================================================
-- int_funnel_stages — Customer journey stage mapping
-- Maps each empresa to their current acquisition/activation stage
-- ============================================================================

CREATE OR REPLACE VIEW int_funnel_stages AS
WITH stage_events AS (
    SELECT
        ea.empresa_id,
        ea.dt_cadastro,
        -- Stage 1: Signup
        ea.dt_cadastro                                          AS dt_signup,

        -- Stage 2: Activation (first pedido published)
        MIN(p.data_publicacao) FILTER (WHERE p.data_publicacao IS NOT NULL) AS dt_first_publish,

        -- Stage 3: First match
        MIN(p.dt_criacao) FILTER (WHERE p.foi_matched)         AS dt_first_match,

        -- Stage 4: First completed order
        MIN(p.dt_criacao) FILTER (WHERE p.foi_finalizado)      AS dt_first_order_complete,

        -- Stage 5: Second order (retention signal)
        MIN(p.dt_criacao) FILTER (
            WHERE p.foi_finalizado AND
            p.dt_criacao > (
                SELECT MIN(p2.dt_criacao)
                FROM stg_pedidos p2
                WHERE p2.empresa_id = ea.empresa_id AND p2.foi_finalizado
            )
        )                                                       AS dt_second_order

    FROM int_empresa_activity ea
    LEFT JOIN stg_pedidos p ON ea.empresa_id = p.empresa_id
    GROUP BY ea.empresa_id, ea.dt_cadastro
)
SELECT
    se.empresa_id,
    ea.nome_fantasia,
    ea.segmento,
    ea.porte,
    ea.estado,

    -- Stage timestamps
    se.dt_signup,
    se.dt_first_publish,
    se.dt_first_match,
    se.dt_first_order_complete,
    se.dt_second_order,

    -- Current stage
    CASE
        WHEN se.dt_second_order IS NOT NULL         THEN 'retained'
        WHEN se.dt_first_order_complete IS NOT NULL THEN 'converted'
        WHEN se.dt_first_match IS NOT NULL          THEN 'matched'
        WHEN se.dt_first_publish IS NOT NULL        THEN 'activated'
        ELSE 'registered'
    END                                             AS current_stage,

    -- Stage number (for funnel ordering)
    CASE
        WHEN se.dt_second_order IS NOT NULL         THEN 5
        WHEN se.dt_first_order_complete IS NOT NULL THEN 4
        WHEN se.dt_first_match IS NOT NULL          THEN 3
        WHEN se.dt_first_publish IS NOT NULL        THEN 2
        ELSE 1
    END                                             AS stage_num,

    -- Time-between-stages (days)
    CASE
        WHEN se.dt_first_publish IS NOT NULL
        THEN EXTRACT(EPOCH FROM (se.dt_first_publish - se.dt_signup)) / 86400
    END::INTEGER                                    AS dias_signup_para_ativacao,

    CASE
        WHEN se.dt_first_match IS NOT NULL AND se.dt_first_publish IS NOT NULL
        THEN EXTRACT(EPOCH FROM (se.dt_first_match - se.dt_first_publish)) / 86400
    END::INTEGER                                    AS dias_ativacao_para_match,

    CASE
        WHEN se.dt_first_order_complete IS NOT NULL AND se.dt_first_match IS NOT NULL
        THEN EXTRACT(EPOCH FROM (se.dt_first_order_complete - se.dt_first_match)) / 86400
    END::INTEGER                                    AS dias_match_para_conversao,

    CASE
        WHEN se.dt_second_order IS NOT NULL AND se.dt_first_order_complete IS NOT NULL
        THEN EXTRACT(EPOCH FROM (se.dt_second_order - se.dt_first_order_complete)) / 86400
    END::INTEGER                                    AS dias_conversao_para_retencao,

    -- Cohort month (for cohort analysis)
    DATE_TRUNC('month', se.dt_signup)               AS cohort_mes,

    -- Additional metrics from activity
    ea.total_pedidos,
    ea.gmv_total,
    ea.lifecycle_stage,
    ea.dias_desde_ultimo_pedido

FROM stage_events se
JOIN int_empresa_activity ea ON se.empresa_id = ea.empresa_id
;
