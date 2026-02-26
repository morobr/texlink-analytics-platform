-- ============================================================================
-- TEXLINK ANALYTICS — PostgreSQL Functions & Triggers
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Function: update_updated_at()
-- Automatically sets updated_at = NOW() before any UPDATE
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER trg_empresas_updated_at
    BEFORE UPDATE ON empresas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_oficinas_updated_at
    BEFORE UPDATE ON oficinas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_usuarios_updated_at
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_pedidos_updated_at
    BEFORE UPDATE ON pedidos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_propostas_updated_at
    BEFORE UPDATE ON propostas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_producao_updated_at
    BEFORE UPDATE ON producao
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_pagamentos_updated_at
    BEFORE UPDATE ON pagamentos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_certificacoes_updated_at
    BEFORE UPDATE ON certificacoes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ----------------------------------------------------------------------------
-- Function: refresh_oficina_scores()
-- Recalculates oficina aggregate scores after a new avaliacao is inserted
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION refresh_oficina_scores()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE oficinas
    SET
        score_qualidade    = (
            SELECT ROUND(AVG(nota_qualidade)::numeric, 2)
            FROM avaliacoes
            WHERE avaliado_oficina_id = NEW.avaliado_oficina_id
              AND nota_qualidade IS NOT NULL
        ),
        score_pontualidade = (
            SELECT ROUND(AVG(nota_pontualidade)::numeric, 2)
            FROM avaliacoes
            WHERE avaliado_oficina_id = NEW.avaliado_oficina_id
              AND nota_pontualidade IS NOT NULL
        ),
        score_comunicacao  = (
            SELECT ROUND(AVG(nota_comunicacao)::numeric, 2)
            FROM avaliacoes
            WHERE avaliado_oficina_id = NEW.avaliado_oficina_id
              AND nota_comunicacao IS NOT NULL
        ),
        total_avaliacoes   = (
            SELECT COUNT(*)
            FROM avaliacoes
            WHERE avaliado_oficina_id = NEW.avaliado_oficina_id
        )
    WHERE id = NEW.avaliado_oficina_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_avaliacao_refresh_scores
    AFTER INSERT OR UPDATE ON avaliacoes
    FOR EACH ROW
    WHEN (NEW.avaliado_oficina_id IS NOT NULL)
    EXECUTE FUNCTION refresh_oficina_scores();

-- ----------------------------------------------------------------------------
-- Function: generate_pedido_codigo()
-- Generates human-readable order codes like PED-2025-00001
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION generate_pedido_codigo()
RETURNS TRIGGER AS $$
DECLARE
    year_str TEXT;
    seq_num  INTEGER;
BEGIN
    year_str := TO_CHAR(NOW(), 'YYYY');
    SELECT COUNT(*) + 1 INTO seq_num
    FROM pedidos
    WHERE EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW());

    NEW.codigo := 'PED-' || year_str || '-' || LPAD(seq_num::TEXT, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_pedidos_generate_codigo
    BEFORE INSERT ON pedidos
    FOR EACH ROW
    WHEN (NEW.codigo IS NULL OR NEW.codigo = '')
    EXECUTE FUNCTION generate_pedido_codigo();

-- ----------------------------------------------------------------------------
-- View: v_platform_summary
-- Quick platform health snapshot for monitoring
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_platform_summary AS
SELECT
    (SELECT COUNT(*) FROM empresas WHERE deleted_at IS NULL AND ativo) AS total_empresas_ativas,
    (SELECT COUNT(*) FROM oficinas WHERE deleted_at IS NULL AND ativo)  AS total_oficinas_ativas,
    (SELECT COUNT(*) FROM pedidos WHERE deleted_at IS NULL)             AS total_pedidos,
    (SELECT COUNT(*) FROM pedidos WHERE status = 'finalizado')          AS pedidos_finalizados,
    (SELECT COALESCE(SUM(valor_bruto), 0) FROM pagamentos WHERE status = 'pago') AS gmv_total,
    (SELECT COALESCE(SUM(taxa_plataforma), 0) FROM pagamentos WHERE status = 'pago') AS receita_total,
    NOW() AS snapshot_at;
