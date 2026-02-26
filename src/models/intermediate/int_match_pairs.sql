-- ============================================================================
-- int_match_pairs — Empresa↔Oficina pairing history
-- Every matched order creates a pair record for relationship analysis
-- ============================================================================

CREATE OR REPLACE VIEW int_match_pairs AS
SELECT
    p.pedido_id,
    p.empresa_id,
    p.oficina_id,

    -- Empresa info
    e.nome_fantasia                             AS empresa_nome,
    e.estado                                    AS empresa_estado,
    e.segmento                                  AS empresa_segmento,
    e.porte                                     AS empresa_porte,

    -- Oficina info
    o.nome_fantasia                             AS oficina_nome,
    o.estado                                    AS oficina_estado,
    o.tier                                      AS oficina_tier,
    o.score_medio                               AS oficina_score_no_match,

    -- Order details
    p.categoria_id,
    p.quantidade_total,
    p.valor_final,
    p.entregue_no_prazo,
    p.foi_finalizado,
    p.dt_criacao                                AS dt_match,

    -- Post-match satisfaction
    a.nota_geral                                AS avaliacao_nota_geral,
    a.nota_qualidade                            AS avaliacao_nota_qualidade,
    a.nota_pontualidade                         AS avaliacao_nota_pontualidade,

    -- Geographic match type
    CASE
        WHEN e.estado = o.estado THEN 'mesmo_estado'
        WHEN e.estado IN ('SC','PR','RS') AND o.estado IN ('SC','PR','RS') THEN 'sul'
        ELSE 'interestadual'
    END                                         AS tipo_match_geografico,

    -- Is this a repeat pairing?
    ROW_NUMBER() OVER (
        PARTITION BY p.empresa_id, p.oficina_id
        ORDER BY p.dt_criacao
    )                                           AS numero_match_no_par,

    -- Match quality score (composite)
    ROUND((
        COALESCE(a.nota_qualidade, o.score_qualidade / 2) +
        COALESCE(a.nota_pontualidade, o.score_pontualidade / 2)
    ) / 2.0, 2)                                AS match_quality_score

FROM stg_pedidos p
JOIN stg_empresas e ON p.empresa_id = e.empresa_id
JOIN stg_oficinas o ON p.oficina_id = o.oficina_id
LEFT JOIN stg_avaliacoes a ON p.pedido_id = a.pedido_id
    AND a.avaliado_oficina_id = p.oficina_id
WHERE p.foi_matched
;
