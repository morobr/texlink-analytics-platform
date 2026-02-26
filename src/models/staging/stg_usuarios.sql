-- ============================================================================
-- stg_usuarios — Staging model for platform users
-- ============================================================================

CREATE OR REPLACE VIEW stg_usuarios AS
SELECT
    u.id                                        AS usuario_id,
    LOWER(TRIM(u.email))                        AS email,
    TRIM(u.nome)                                AS nome,
    REGEXP_REPLACE(u.telefone, '\D', '', 'g')   AS telefone_limpo,
    u.role,

    -- Entity linkage
    u.empresa_id,
    u.oficina_id,

    -- Derived entity type
    CASE
        WHEN u.role IN ('empresa_owner', 'empresa_user') THEN 'empresa'
        WHEN u.role IN ('oficina_owner', 'oficina_user') THEN 'oficina'
        ELSE 'admin'
    END                                         AS tipo_entidade,

    -- Is owner flag
    u.role IN ('empresa_owner', 'oficina_owner') AS is_owner,

    -- Activity
    u.ultimo_login,
    COALESCE(u.login_count, 0)                  AS login_count,
    u.ativo,

    -- Days since last login (NULL if never logged in)
    CASE
        WHEN u.ultimo_login IS NOT NULL
        THEN EXTRACT(EPOCH FROM (NOW() - u.ultimo_login)) / 86400
    END::INTEGER                                AS dias_desde_ultimo_login,

    -- Active in last 30 days
    u.ultimo_login >= NOW() - INTERVAL '30 days' AS ativo_ultimos_30d,

    -- Timestamps
    u.created_at                                AS dt_cadastro,
    u.updated_at                                AS dt_atualizacao,
    u.deleted_at                                AS dt_exclusao

FROM usuarios u
WHERE u.deleted_at IS NULL
;
