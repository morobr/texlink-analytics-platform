-- ============================================================================
-- TEXLINK ANALYTICS — Performance Indexes
-- ============================================================================

-- empresas
CREATE INDEX idx_empresas_estado ON empresas(estado) WHERE deleted_at IS NULL;
CREATE INDEX idx_empresas_porte ON empresas(porte) WHERE deleted_at IS NULL;
CREATE INDEX idx_empresas_created_at ON empresas(created_at);

-- oficinas
CREATE INDEX idx_oficinas_estado ON oficinas(estado) WHERE deleted_at IS NULL;
CREATE INDEX idx_oficinas_tier ON oficinas(tier) WHERE deleted_at IS NULL;
CREATE INDEX idx_oficinas_score ON oficinas(score_qualidade DESC) WHERE deleted_at IS NULL;

-- usuarios
CREATE INDEX idx_usuarios_empresa ON usuarios(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_usuarios_oficina ON usuarios(oficina_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_usuarios_ultimo_login ON usuarios(ultimo_login DESC);

-- pedidos
CREATE INDEX idx_pedidos_empresa ON pedidos(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_pedidos_oficina ON pedidos(oficina_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_pedidos_status ON pedidos(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_pedidos_created_at ON pedidos(created_at);
CREATE INDEX idx_pedidos_categoria ON pedidos(categoria_id);

-- propostas
CREATE INDEX idx_propostas_pedido ON propostas(pedido_id);
CREATE INDEX idx_propostas_oficina ON propostas(oficina_id);
CREATE INDEX idx_propostas_status ON propostas(status);
CREATE INDEX idx_propostas_created_at ON propostas(created_at);

-- pagamentos
CREATE INDEX idx_pagamentos_pedido ON pagamentos(pedido_id);
CREATE INDEX idx_pagamentos_empresa ON pagamentos(empresa_id);
CREATE INDEX idx_pagamentos_status ON pagamentos(status);
CREATE INDEX idx_pagamentos_data ON pagamentos(data_pagamento);

-- avaliacoes
CREATE INDEX idx_avaliacoes_pedido ON avaliacoes(pedido_id);
CREATE INDEX idx_avaliacoes_oficina ON avaliacoes(avaliado_oficina_id);
CREATE INDEX idx_avaliacoes_empresa ON avaliacoes(avaliado_empresa_id);

-- certificacoes
CREATE INDEX idx_certificacoes_oficina ON certificacoes(oficina_id);
CREATE INDEX idx_certificacoes_tipo ON certificacoes(tipo) WHERE ativo = TRUE;

-- eventos_plataforma (high-volume — partial indexes by tipo)
CREATE INDEX idx_eventos_usuario ON eventos_plataforma(usuario_id, created_at);
CREATE INDEX idx_eventos_tipo ON eventos_plataforma(tipo, created_at);
CREATE INDEX idx_eventos_session ON eventos_plataforma(session_id);
CREATE INDEX idx_eventos_created_at ON eventos_plataforma(created_at);
CREATE INDEX idx_eventos_metadata ON eventos_plataforma USING GIN(metadata);

-- mensagens
CREATE INDEX idx_mensagens_remetente ON mensagens(remetente_id, created_at);
CREATE INDEX idx_mensagens_destinatario ON mensagens(destinatario_id) WHERE lida = FALSE;
CREATE INDEX idx_mensagens_pedido ON mensagens(pedido_id);

-- producao
CREATE INDEX idx_producao_pedido ON producao(pedido_id);
CREATE INDEX idx_producao_oficina ON producao(oficina_id);
CREATE INDEX idx_producao_status ON producao(status);
