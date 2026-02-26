-- ============================================================================
-- stg_pagamentos — Staging model for payment transactions
-- ============================================================================

CREATE OR REPLACE VIEW stg_pagamentos AS
SELECT
    pg.id                                       AS pagamento_id,
    pg.pedido_id,
    pg.empresa_id,
    pg.oficina_id,

    -- Amounts
    ROUND(pg.valor_bruto, 2)                    AS valor_bruto,
    ROUND(pg.taxa_plataforma, 2)                AS taxa_plataforma,
    ROUND(pg.valor_liquido, 2)                  AS valor_liquido,
    ROUND(pg.percentual_taxa, 4)                AS pct_taxa,

    pg.metodo,
    pg.status,
    pg.referencia_externa,

    -- Timeline
    pg.data_vencimento,
    pg.data_pagamento,

    -- Days to pay (from creation to payment)
    CASE
        WHEN pg.data_pagamento IS NOT NULL
        THEN EXTRACT(EPOCH FROM (pg.data_pagamento - pg.created_at)) / 86400
    END::INTEGER                                AS dias_para_pagamento,

    -- Overdue flag
    CASE
        WHEN pg.status = 'pago'    THEN FALSE
        WHEN pg.data_vencimento IS NULL THEN NULL
        WHEN pg.data_vencimento < CURRENT_DATE THEN TRUE
        ELSE FALSE
    END                                         AS em_atraso,

    -- Status flags
    pg.status = 'pago'                          AS foi_pago,
    pg.status = 'estornado'                     AS foi_estornado,
    pg.status IN ('falha', 'estornado')         AS nao_efetivado,

    -- Timestamps
    pg.created_at                               AS dt_criacao,
    pg.updated_at                               AS dt_atualizacao,

    -- Calendar helpers
    DATE_TRUNC('month', COALESCE(pg.data_pagamento, pg.created_at)) AS mes_pagamento,
    EXTRACT(YEAR FROM COALESCE(pg.data_pagamento, pg.created_at))::INTEGER AS ano_pagamento

FROM pagamentos pg
;
