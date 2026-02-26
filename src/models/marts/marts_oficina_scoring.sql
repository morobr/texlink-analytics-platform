-- ============================================================================
-- marts_oficina_scoring — Composite workshop quality scoring
-- Multi-dimensional score driving marketplace ranking and recommendations
-- ============================================================================

CREATE OR REPLACE VIEW marts_oficina_scoring AS
WITH raw_scores AS (
    SELECT
        op.oficina_id,
        op.nome_fantasia,
        op.estado,
        op.cidade,
        op.tier,
        op.capacidade_mensal_pecas,

        -- === DIMENSION 1: Quality (30%) ===
        -- From ratings (if available) else from stored scores
        CASE
            WHEN op.total_avaliacoes >= 3
            THEN op.nota_qualidade_media
            ELSE op.score_qualidade_media * 2  -- Convert 0-10 → 1-5 scale
        END                                                     AS raw_score_qualidade,

        -- === DIMENSION 2: Reliability/Punctuality (25%) ===
        CASE
            WHEN op.total_avaliacoes >= 3
            THEN op.nota_pontualidade_media
            ELSE op.score_pontualidade_media * 2
        END                                                     AS raw_score_pontualidade,

        -- === DIMENSION 3: Communication (15%) ===
        CASE
            WHEN op.total_avaliacoes >= 3
            THEN op.nota_comunicacao_media
            ELSE op.score_comunicacao_media * 2
        END                                                     AS raw_score_comunicacao,

        -- === DIMENSION 4: Volume/Experience (15%) ===
        -- Normalize: 0 orders = 1, 50+ orders = 5
        LEAST(5, 1 + op.total_pedidos::NUMERIC / 12.5)         AS raw_score_experiencia,

        -- === DIMENSION 5: Certifications (10%) ===
        -- Map cert score to 1-5
        LEAST(5, 1 + op.score_certificacoes::NUMERIC / 6)      AS raw_score_certificacoes,

        -- === DIMENSION 6: Response time (5%) ===
        -- 0-1h → 5, 1-4h → 4, 4-12h → 3, 12-24h → 2, 24h+ → 1
        CASE
            WHEN op.tempo_medio_resposta_h <= 1   THEN 5
            WHEN op.tempo_medio_resposta_h <= 4   THEN 4
            WHEN op.tempo_medio_resposta_h <= 12  THEN 3
            WHEN op.tempo_medio_resposta_h <= 24  THEN 2
            ELSE 1
        END                                                     AS raw_score_velocidade,

        -- Raw metrics for reference
        op.total_pedidos,
        op.pedidos_finalizados,
        op.total_avaliacoes,
        op.win_rate_pct,
        op.taxa_aprovacao_media_pct,
        op.pct_entrega_no_prazo,
        op.tempo_medio_resposta_h,
        op.total_certificacoes,
        op.tem_abvtex,
        op.tem_cert_premium,
        op.ativo_recente

    FROM int_oficina_performance op
    WHERE op.score_qualidade_media IS NOT NULL
       OR op.total_avaliacoes > 0
)
SELECT
    rs.oficina_id,
    rs.nome_fantasia,
    rs.estado,
    rs.cidade,
    rs.tier,
    rs.capacidade_mensal_pecas,

    -- === COMPOSITE SCORE (0-10 scale) ===
    ROUND((
        COALESCE(rs.raw_score_qualidade, 3)    * 0.30 +
        COALESCE(rs.raw_score_pontualidade, 3) * 0.25 +
        COALESCE(rs.raw_score_comunicacao, 3)  * 0.15 +
        COALESCE(rs.raw_score_experiencia, 1)  * 0.15 +
        COALESCE(rs.raw_score_certificacoes, 1) * 0.10 +
        COALESCE(rs.raw_score_velocidade, 3)   * 0.05
    ) * 2.0, 2)                                             AS score_composto,  -- multiply by 2 to get 0-10

    -- Individual dimension scores (1-5)
    ROUND(COALESCE(rs.raw_score_qualidade, 3), 2)           AS score_qualidade,
    ROUND(COALESCE(rs.raw_score_pontualidade, 3), 2)        AS score_pontualidade,
    ROUND(COALESCE(rs.raw_score_comunicacao, 3), 2)         AS score_comunicacao,
    ROUND(COALESCE(rs.raw_score_experiencia, 1), 2)         AS score_experiencia,
    ROUND(COALESCE(rs.raw_score_certificacoes, 1), 2)       AS score_certificacoes,
    COALESCE(rs.raw_score_velocidade, 3)                    AS score_velocidade,

    -- Performance metrics
    rs.total_pedidos,
    rs.pedidos_finalizados,
    rs.total_avaliacoes,
    rs.win_rate_pct,
    rs.taxa_aprovacao_media_pct,
    rs.pct_entrega_no_prazo,
    rs.tempo_medio_resposta_h,
    rs.total_certificacoes,
    rs.tem_abvtex,
    rs.tem_cert_premium,
    rs.ativo_recente,

    -- Ranking tier based on score
    CASE
        WHEN ROUND((
            COALESCE(rs.raw_score_qualidade, 3)    * 0.30 +
            COALESCE(rs.raw_score_pontualidade, 3) * 0.25 +
            COALESCE(rs.raw_score_comunicacao, 3)  * 0.15 +
            COALESCE(rs.raw_score_experiencia, 1)  * 0.15 +
            COALESCE(rs.raw_score_certificacoes, 1) * 0.10 +
            COALESCE(rs.raw_score_velocidade, 3)   * 0.05
        ) * 2.0, 2) >= 8.5 THEN 'elite'
        WHEN ROUND((
            COALESCE(rs.raw_score_qualidade, 3)    * 0.30 +
            COALESCE(rs.raw_score_pontualidade, 3) * 0.25 +
            COALESCE(rs.raw_score_comunicacao, 3)  * 0.15 +
            COALESCE(rs.raw_score_experiencia, 1)  * 0.15 +
            COALESCE(rs.raw_score_certificacoes, 1) * 0.10 +
            COALESCE(rs.raw_score_velocidade, 3)   * 0.05
        ) * 2.0, 2) >= 7.0 THEN 'premium'
        WHEN ROUND((
            COALESCE(rs.raw_score_qualidade, 3)    * 0.30 +
            COALESCE(rs.raw_score_pontualidade, 3) * 0.25 +
            COALESCE(rs.raw_score_comunicacao, 3)  * 0.15 +
            COALESCE(rs.raw_score_experiencia, 1)  * 0.15 +
            COALESCE(rs.raw_score_certificacoes, 1) * 0.10 +
            COALESCE(rs.raw_score_velocidade, 3)   * 0.05
        ) * 2.0, 2) >= 5.0 THEN 'standard'
        ELSE 'basico'
    END                                                     AS ranking_tier,

    -- Percentile rank
    PERCENT_RANK() OVER (
        ORDER BY ROUND((
            COALESCE(rs.raw_score_qualidade, 3)    * 0.30 +
            COALESCE(rs.raw_score_pontualidade, 3) * 0.25 +
            COALESCE(rs.raw_score_comunicacao, 3)  * 0.15 +
            COALESCE(rs.raw_score_experiencia, 1)  * 0.15 +
            COALESCE(rs.raw_score_certificacoes, 1) * 0.10 +
            COALESCE(rs.raw_score_velocidade, 3)   * 0.05
        ) * 2.0, 2)
    ) * 100                                                 AS percentil_rank

FROM raw_scores rs
ORDER BY score_composto DESC
;
