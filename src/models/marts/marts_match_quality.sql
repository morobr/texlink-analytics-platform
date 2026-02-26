-- ============================================================================
-- marts_match_quality — Matching effectiveness analysis
-- Empresa↔Oficina pairing performance and coverage gaps
-- ============================================================================

CREATE OR REPLACE VIEW marts_match_quality AS
WITH pair_stats AS (
    SELECT
        mp.empresa_estado,
        mp.oficina_estado,
        mp.tipo_match_geografico,
        mp.empresa_segmento,
        mp.oficina_tier,
        COUNT(*)                                                AS total_matches,
        COUNT(*) FILTER (WHERE mp.foi_finalizado)              AS matches_finalizados,
        ROUND(AVG(mp.match_quality_score), 2)                  AS avg_match_quality,
        ROUND(AVG(mp.avaliacao_nota_geral), 2)                 AS avg_satisfaction,
        ROUND(AVG(mp.quantidade_total), 0)                     AS avg_qty_matched,
        ROUND(SUM(mp.valor_final), 2)                          AS gmv_matched,
        COUNT(*) FILTER (WHERE mp.numero_match_no_par > 1)     AS repeat_pairs,
        ROUND(AVG(mp.numero_match_no_par), 2)                  AS avg_ordens_por_par
    FROM int_match_pairs mp
    GROUP BY
        mp.empresa_estado,
        mp.oficina_estado,
        mp.tipo_match_geografico,
        mp.empresa_segmento,
        mp.oficina_tier
),
demand_supply_by_state AS (
    SELECT
        e.estado,
        COUNT(DISTINCT p.empresa_id) FILTER (WHERE p.pedido_id IS NOT NULL) AS empresas_com_pedidos,
        COUNT(DISTINCT p.pedido_id)                             AS total_pedidos_publicados,
        COUNT(DISTINCT p.pedido_id) FILTER (WHERE p.foi_matched) AS pedidos_matched_local,
        (SELECT COUNT(*) FROM stg_oficinas o2
         WHERE o2.estado = e.estado AND o2.ativo)               AS oficinas_ativas_local
    FROM stg_empresas e
    LEFT JOIN stg_pedidos p ON e.empresa_id = p.empresa_id
        AND p.data_publicacao IS NOT NULL
    GROUP BY e.estado
)
SELECT
    ps.empresa_estado,
    ps.oficina_estado,
    ps.tipo_match_geografico,
    ps.empresa_segmento,
    ps.oficina_tier,
    ps.total_matches,
    ps.matches_finalizados,
    ROUND(ps.matches_finalizados::NUMERIC / NULLIF(ps.total_matches, 0) * 100, 2) AS pct_finalizado,
    ps.avg_match_quality,
    ps.avg_satisfaction,
    ps.avg_qty_matched,
    ROUND(ps.gmv_matched, 2)                    AS gmv_matched,
    ps.repeat_pairs,
    ROUND(ps.repeat_pairs::NUMERIC / NULLIF(ps.total_matches, 0) * 100, 2) AS pct_repeat,
    ps.avg_ordens_por_par

FROM pair_stats ps
ORDER BY ps.total_matches DESC
;
