-- ============================================================================
-- stg_pedido_items — Staging model for order line items
-- ============================================================================

CREATE OR REPLACE VIEW stg_pedido_items AS
SELECT
    pi.id                                       AS item_id,
    pi.pedido_id,

    TRIM(pi.descricao)                          AS descricao,
    pi.quantidade,
    UPPER(TRIM(COALESCE(pi.tamanho, 'UNI')))    AS tamanho,
    TRIM(pi.cor)                                AS cor,
    TRIM(pi.material)                           AS material,
    ROUND(COALESCE(pi.valor_unitario, 0), 2)    AS valor_unitario,

    -- Line total
    ROUND(pi.quantidade * COALESCE(pi.valor_unitario, 0), 2) AS valor_total_item,

    pi.observacoes,
    pi.created_at                               AS dt_criacao

FROM pedido_items pi
JOIN pedidos p ON pi.pedido_id = p.id
WHERE p.deleted_at IS NULL
;
