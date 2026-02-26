"""
Tests for seed data generator.
Validates generated data structure, types, and referential integrity.
"""

import pytest
from src.seeds.seed_generator import TexlinkSeeder, load_config


@pytest.fixture(scope="module")
def dataset():
    """Generate a small dataset for testing."""
    cfg = load_config("src/seeds/seed_config.yaml")
    # Reduce volumes for fast test
    cfg["empresas"] = 20
    cfg["oficinas"] = 40
    cfg["pedidos_total"] = 100
    cfg["eventos_total"] = 500
    seeder = TexlinkSeeder(cfg)
    return seeder.generate_all()


def test_categorias_generated(dataset):
    assert len(dataset.categorias) > 0
    for cat in dataset.categorias:
        assert "id" in cat
        assert "nome" in cat
        assert cat["nivel"] in (1, 2)


def test_empresas_generated(dataset):
    assert len(dataset.empresas) == 20
    for emp in dataset.empresas:
        assert "id" in emp
        assert emp["cnpj"] is not None
        assert emp["estado"] in ["SC", "SP", "CE", "MG", "PR", "RS"]
        assert emp["porte"] in ["micro", "pequena", "media", "grande"]


def test_oficinas_generated(dataset):
    assert len(dataset.oficinas) == 40
    for of in dataset.oficinas:
        assert "id" in of
        assert of["tier"] in ["bronze", "prata", "ouro", "diamante"]
        assert isinstance(of["especialidades"], list)
        assert len(of["especialidades"]) >= 2


def test_usuarios_generated(dataset):
    assert len(dataset.usuarios) > 0

    roles = {u["role"] for u in dataset.usuarios}
    assert "empresa_owner" in roles
    assert "oficina_owner" in roles
    assert "admin" in roles

    # Every empresa_user must have empresa_id
    for u in dataset.usuarios:
        if u["role"] in ("empresa_owner", "empresa_user"):
            assert u["empresa_id"] is not None
            assert u["oficina_id"] is None
        elif u["role"] in ("oficina_owner", "oficina_user"):
            assert u["oficina_id"] is not None
            assert u["empresa_id"] is None


def test_pedidos_referential_integrity(dataset):
    empresa_ids = {e["id"] for e in dataset.empresas}
    oficina_ids = {o["id"] for o in dataset.oficinas}

    for p in dataset.pedidos:
        assert p["empresa_id"] in empresa_ids, f"Invalid empresa_id: {p['empresa_id']}"
        if p["oficina_id"] is not None:
            assert p["oficina_id"] in oficina_ids, f"Invalid oficina_id: {p['oficina_id']}"


def test_pedido_statuses(dataset):
    valid_statuses = {
        "rascunho", "publicado", "em_negociacao", "confirmado",
        "em_producao", "controle_qualidade", "entregue", "finalizado",
        "cancelado", "disputa",
    }
    for p in dataset.pedidos:
        assert p["status"] in valid_statuses, f"Invalid status: {p['status']}"


def test_propostas_reference_valid_entities(dataset):
    pedido_ids = {p["id"] for p in dataset.pedidos}
    oficina_ids = {o["id"] for o in dataset.oficinas}

    for pr in dataset.propostas:
        assert pr["pedido_id"] in pedido_ids
        assert pr["oficina_id"] in oficina_ids


def test_pagamentos_only_for_finalized(dataset):
    finalized_pedido_ids = {p["id"] for p in dataset.pedidos if p["status"] == "finalizado"}
    for pg in dataset.pagamentos:
        assert pg["pedido_id"] in finalized_pedido_ids, \
            f"Payment for non-finalized pedido: {pg['pedido_id']}"


def test_avaliacoes_direction_constraint(dataset):
    for av in dataset.avaliacoes:
        has_empresa = av["avaliado_empresa_id"] is not None
        has_oficina = av["avaliado_oficina_id"] is not None
        assert has_empresa ^ has_oficina, \
            "Avaliacao must rate either empresa OR oficina, not both/neither"


def test_certificacoes_for_valid_oficinas(dataset):
    oficina_ids = {o["id"] for o in dataset.oficinas}
    for c in dataset.certificacoes:
        assert c["oficina_id"] in oficina_ids


def test_eventos_have_valid_users(dataset):
    usuario_ids = {u["id"] for u in dataset.usuarios}
    for e in dataset.eventos_plataforma:
        if e["usuario_id"] is not None:
            assert e["usuario_id"] in usuario_ids
