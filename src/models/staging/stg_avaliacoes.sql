-- ============================================================================
-- stg_avaliacoes — Staging model for ratings/reviews
-- ============================================================================

CREATE OR REPLACE VIEW stg_avaliacoes AS
SELECT
    a.id                                        AS avaliacao_id,
    a.pedido_id,
    a.avaliador_id,
    a.avaliado_empresa_id,
    a.avaliado_oficina_id,

    -- Direction of review
    CASE
        WHEN a.avaliado_oficina_id IS NOT NULL THEN 'empresa_avalia_oficina'
        WHEN a.avaliado_empresa_id IS NOT NULL THEN 'oficina_avalia_empresa'
    END                                         AS direcao_avaliacao,

    -- Scores
    a.nota_geral,
    COALESCE(a.nota_qualidade, a.nota_geral)    AS nota_qualidade,
    COALESCE(a.nota_pontualidade, a.nota_geral) AS nota_pontualidade,
    COALESCE(a.nota_comunicacao, a.nota_geral)  AS nota_comunicacao,
    COALESCE(a.nota_custo_beneficio, a.nota_geral) AS nota_custo_beneficio,

    -- Average across all dimensions
    ROUND((
        a.nota_geral +
        COALESCE(a.nota_qualidade, a.nota_geral) +
        COALESCE(a.nota_pontualidade, a.nota_geral) +
        COALESCE(a.nota_comunicacao, a.nota_geral) +
        COALESCE(a.nota_custo_beneficio, a.nota_geral)
    ) / 5.0, 2)                                AS nota_media_dimensoes,

    -- Score on 0-10 scale (for consistency with oficina scores)
    ROUND(a.nota_geral * 2.0, 2)               AS nota_geral_10,

    -- Sentiment
    CASE
        WHEN a.nota_geral >= 5 THEN 'positivo'
        WHEN a.nota_geral = 3  THEN 'neutro'
        ELSE 'negativo'
    END                                         AS sentimento,

    a.comentario,
    a.comentario IS NOT NULL                    AS tem_comentario,
    a.publica,

    -- Timestamps
    a.created_at                                AS dt_avaliacao

FROM avaliacoes a
;
