-- ============================================================================
-- marts_geographic_analysis — Regional supply-demand balance
-- ============================================================================

CREATE OR REPLACE VIEW marts_geographic_analysis AS
WITH demand_by_state AS (
    SELECT
        e.estado,
        COUNT(DISTINCT e.empresa_id)            AS total_empresas,
        COUNT(DISTINCT e.empresa_id) FILTER (WHERE e.ativo) AS empresas_ativas,
        COUNT(DISTINCT p.pedido_id)             AS total_pedidos,
        COUNT(DISTINCT p.pedido_id) FILTER (WHERE p.status = 'publicado' OR p.data_publicacao IS NOT NULL) AS pedidos_publicados,
        COUNT(DISTINCT p.pedido_id) FILTER (WHERE p.foi_matched) AS pedidos_matched,
        ROUND(SUM(p.valor_estimado), 2)         AS demanda_estimada_brl,
        ROUND(SUM(p.valor_final) FILTER (WHERE p.foi_finalizado), 2) AS gmv_estado
    FROM stg_empresas e
    LEFT JOIN stg_pedidos p ON e.empresa_id = p.empresa_id
    GROUP BY e.estado
),
supply_by_state AS (
    SELECT
        o.estado,
        COUNT(DISTINCT o.oficina_id)            AS total_oficinas,
        COUNT(DISTINCT o.oficina_id) FILTER (WHERE o.ativo) AS oficinas_ativas,
        SUM(o.capacidade_mensal_pecas)          AS capacidade_total_mensal,
        ROUND(AVG(o.score_medio), 2)            AS score_medio_estado,
        COUNT(DISTINCT o.oficina_id) FILTER (WHERE o.tier = 'ouro') AS oficinas_ouro,
        COUNT(DISTINCT o.oficina_id) FILTER (WHERE o.tier = 'diamante') AS oficinas_diamante
    FROM stg_oficinas o
    GROUP BY o.estado
),
certification_by_state AS (
    SELECT
        of.estado,
        COUNT(DISTINCT c.certificacao_id)       AS total_certificacoes,
        COUNT(DISTINCT of.oficina_id) FILTER (WHERE c.tipo = 'abvtex') AS oficinas_abvtex
    FROM stg_oficinas of
    LEFT JOIN stg_certificacoes c ON of.oficina_id = c.oficina_id
    GROUP BY of.estado
)
SELECT
    COALESCE(d.estado, s.estado)                AS estado,

    -- Demand
    COALESCE(d.total_empresas, 0)               AS total_empresas,
    COALESCE(d.empresas_ativas, 0)              AS empresas_ativas,
    COALESCE(d.total_pedidos, 0)                AS total_pedidos,
    COALESCE(d.pedidos_publicados, 0)           AS pedidos_publicados,
    COALESCE(d.pedidos_matched, 0)              AS pedidos_matched,
    ROUND(COALESCE(d.demanda_estimada_brl, 0), 2) AS demanda_estimada_brl,
    ROUND(COALESCE(d.gmv_estado, 0), 2)         AS gmv_estado,

    -- Supply
    COALESCE(s.total_oficinas, 0)               AS total_oficinas,
    COALESCE(s.oficinas_ativas, 0)              AS oficinas_ativas,
    COALESCE(s.capacidade_total_mensal, 0)      AS capacidade_mensal_pecas,
    COALESCE(s.score_medio_estado, 0)           AS score_medio_oficinas,
    COALESCE(s.oficinas_ouro, 0)                AS oficinas_ouro,
    COALESCE(s.oficinas_diamante, 0)            AS oficinas_diamante,

    -- Certifications
    COALESCE(c.total_certificacoes, 0)          AS total_certificacoes,
    COALESCE(c.oficinas_abvtex, 0)              AS oficinas_abvtex,

    -- Supply-demand ratio
    CASE
        WHEN COALESCE(d.total_empresas, 0) > 0
        THEN ROUND(COALESCE(s.total_oficinas, 0)::NUMERIC / d.total_empresas, 2)
    END                                         AS ratio_oficinas_por_empresa,

    -- Match rate by state
    CASE
        WHEN COALESCE(d.pedidos_publicados, 0) > 0
        THEN ROUND(d.pedidos_matched::NUMERIC / d.pedidos_publicados * 100, 2)
    END                                         AS match_rate_pct,

    -- Balance assessment
    CASE
        WHEN COALESCE(s.total_oficinas, 0) = 0 THEN 'sem_oferta'
        WHEN COALESCE(d.total_empresas, 0) = 0 THEN 'sem_demanda'
        WHEN COALESCE(s.total_oficinas, 0)::NUMERIC /
             NULLIF(COALESCE(d.total_empresas, 0), 0) >= 3 THEN 'excesso_oferta'
        WHEN COALESCE(s.total_oficinas, 0)::NUMERIC /
             NULLIF(COALESCE(d.total_empresas, 0), 0) >= 1.5 THEN 'equilibrado'
        WHEN COALESCE(s.total_oficinas, 0)::NUMERIC /
             NULLIF(COALESCE(d.total_empresas, 0), 0) >= 0.5 THEN 'escassez_leve'
        ELSE 'escassez_critica'
    END                                         AS balanco_mercado

FROM demand_by_state d
FULL OUTER JOIN supply_by_state s ON d.estado = s.estado
LEFT JOIN certification_by_state c ON COALESCE(d.estado, s.estado) = c.estado
ORDER BY gmv_estado DESC NULLS LAST
;
