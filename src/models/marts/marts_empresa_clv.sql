-- ============================================================================
-- marts_empresa_clv — Customer Lifetime Value estimates for brands
-- SQL-based CLV using RFM + historical patterns
-- (Full Bayesian CLV is in src/analytics/clv_model.py)
-- ============================================================================

CREATE OR REPLACE VIEW marts_empresa_clv AS
WITH rfm AS (
    SELECT
        empresa_id,
        -- Recency: days since last order
        EXTRACT(EPOCH FROM (NOW() - MAX(dt_criacao))) / 86400   AS recency_days,
        -- Frequency: total completed orders
        COUNT(*) FILTER (WHERE foi_finalizado)                  AS frequency,
        -- Monetary: avg order value
        ROUND(AVG(valor_final) FILTER (WHERE foi_finalizado), 2) AS monetary_avg,
        -- Total spend
        ROUND(SUM(valor_final) FILTER (WHERE foi_finalizado), 2) AS total_spend,
        -- First order date
        MIN(dt_criacao) FILTER (WHERE foi_finalizado)           AS first_order_date,
        -- Last order date
        MAX(dt_criacao) FILTER (WHERE foi_finalizado)           AS last_order_date,
        -- Customer age in months
        EXTRACT(EPOCH FROM (MAX(dt_criacao) - MIN(dt_criacao))) / (86400 * 30) AS age_months
    FROM stg_pedidos
    GROUP BY empresa_id
),
rfm_scores AS (
    SELECT
        *,
        -- RFM scoring (quintiles 1-5)
        NTILE(5) OVER (ORDER BY recency_days DESC)              AS r_score,
        NTILE(5) OVER (ORDER BY frequency)                      AS f_score,
        NTILE(5) OVER (ORDER BY monetary_avg NULLS LAST)        AS m_score
    FROM rfm
    WHERE frequency > 0
),
clv_calc AS (
    SELECT
        rs.empresa_id,
        rs.recency_days,
        rs.frequency,
        rs.monetary_avg,
        rs.total_spend,
        rs.first_order_date,
        rs.last_order_date,
        rs.age_months,
        rs.r_score,
        rs.f_score,
        rs.m_score,

        -- Composite RFM score
        ROUND((rs.r_score * 0.3 + rs.f_score * 0.4 + rs.m_score * 0.3), 2) AS rfm_score,

        -- Purchase interval: avg days between orders
        CASE
            WHEN rs.frequency > 1 AND rs.age_months > 0
            THEN ROUND(rs.age_months * 30 / (rs.frequency - 1), 1)
        END                                                     AS avg_days_between_orders,

        -- Simple CLV projection: AOV × expected future orders in 12 months
        -- Expected future orders = frequency / age_months * 12 * churn_discount
        CASE
            WHEN rs.age_months > 0.5 AND rs.frequency > 0
            THEN ROUND(
                rs.monetary_avg *
                (rs.frequency / NULLIF(rs.age_months, 0)) * 12 *
                -- Churn discount based on recency
                CASE
                    WHEN rs.recency_days <= 30  THEN 0.85
                    WHEN rs.recency_days <= 90  THEN 0.65
                    WHEN rs.recency_days <= 180 THEN 0.40
                    ELSE 0.15
                END,
            2)
        END                                                     AS clv_12m_estimate,

        -- Historical CLV (realized)
        rs.total_spend                                          AS clv_historico

    FROM rfm_scores rs
)
SELECT
    cc.empresa_id,
    e.nome_fantasia,
    e.segmento,
    e.porte,
    e.estado,

    -- RFM
    ROUND(cc.recency_days::NUMERIC, 0)          AS recencia_dias,
    cc.frequency                                AS frequencia,
    ROUND(cc.monetary_avg, 2)                   AS ticket_medio,
    ROUND(cc.total_spend, 2)                    AS gasto_total,
    cc.r_score,
    cc.f_score,
    cc.m_score,
    cc.rfm_score,

    -- CLV
    ROUND(cc.clv_12m_estimate, 2)               AS clv_12m_estimado,
    ROUND(cc.clv_historico, 2)                  AS clv_historico,
    ROUND(cc.avg_days_between_orders, 1)        AS intervalo_medio_pedidos_dias,

    -- Timeline
    cc.first_order_date,
    cc.last_order_date,
    ROUND(cc.age_months::NUMERIC, 1)            AS antiguidade_meses,

    -- Segment
    CASE
        WHEN cc.rfm_score >= 4.0 THEN 'champions'
        WHEN cc.rfm_score >= 3.5 THEN 'loyal_customers'
        WHEN cc.rfm_score >= 3.0 AND cc.r_score >= 4 THEN 'potential_loyalists'
        WHEN cc.rfm_score >= 3.0 AND cc.r_score <= 2 THEN 'at_risk'
        WHEN cc.r_score <= 2 AND cc.f_score <= 2 THEN 'lost'
        ELSE 'need_attention'
    END                                         AS rfm_segment,

    -- Churn probability (heuristic)
    CASE
        WHEN cc.recency_days <= 30  THEN 0.05
        WHEN cc.recency_days <= 90  THEN 0.20
        WHEN cc.recency_days <= 180 THEN 0.50
        ELSE 0.80
    END                                         AS prob_churn_estimada

FROM clv_calc cc
JOIN stg_empresas e ON cc.empresa_id = e.empresa_id
ORDER BY cc.clv_12m_estimate DESC NULLS LAST
;
