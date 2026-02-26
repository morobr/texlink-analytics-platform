-- ============================================================================
-- stg_eventos_plataforma — Staging model for platform clickstream events
-- ============================================================================

CREATE OR REPLACE VIEW stg_eventos_plataforma AS
SELECT
    e.id                                        AS evento_id,
    e.usuario_id,
    e.session_id,

    e.tipo,
    TRIM(e.pagina)                              AS pagina,
    e.referrer,

    e.entidade_tipo,
    e.entidade_id,
    e.metadata,

    -- Device & location
    e.ip_address::TEXT                          AS ip_address,
    e.user_agent,
    COALESCE(e.dispositivo, 'desconhecido')     AS dispositivo,

    -- Event category grouping
    CASE
        WHEN e.tipo IN ('page_view', 'login', 'logout')         THEN 'navegacao'
        WHEN e.tipo IN ('signup_started', 'signup_completed')   THEN 'cadastro'
        WHEN e.tipo IN ('pedido_created', 'pedido_published')   THEN 'pedido'
        WHEN e.tipo IN ('proposta_sent', 'proposta_viewed', 'proposta_aceita') THEN 'proposta'
        WHEN e.tipo IN ('mensagem_sent')                        THEN 'comunicacao'
        WHEN e.tipo IN ('pagamento_initiated')                  THEN 'financeiro'
        WHEN e.tipo IN ('avaliacao_submitted')                  THEN 'qualidade'
        WHEN e.tipo IN ('search_performed', 'oficina_viewed')   THEN 'descoberta'
        ELSE 'outros'
    END                                         AS categoria_evento,

    -- Timestamps
    e.created_at                                AS dt_evento,
    DATE_TRUNC('hour', e.created_at)            AS hora_evento,
    DATE_TRUNC('day', e.created_at)             AS dia_evento,
    DATE_TRUNC('week', e.created_at)            AS semana_evento,
    EXTRACT(HOUR FROM e.created_at)::INTEGER    AS hora_do_dia,
    EXTRACT(DOW FROM e.created_at)::INTEGER     AS dia_semana  -- 0=Sunday

FROM eventos_plataforma e
;
