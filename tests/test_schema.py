"""
Tests for database schema integrity.
Requires a running PostgreSQL with the schema loaded.
"""

import os
import pytest
import psycopg2
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="module")
def conn():
    db_url = os.getenv("DATABASE_URL", "postgresql://texlink:password@localhost:5432/texlink_test")
    c = psycopg2.connect(db_url)
    yield c
    c.close()


EXPECTED_TABLES = [
    "categorias_produto", "empresas", "oficinas", "usuarios",
    "pedidos", "pedido_items", "propostas", "producao",
    "avaliacoes", "certificacoes", "pagamentos",
    "mensagens", "eventos_plataforma", "notificacoes",
]


def test_all_tables_exist(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        existing = {row[0] for row in cur.fetchall()}

    for table in EXPECTED_TABLES:
        assert table in existing, f"Table '{table}' not found in schema"


def test_uuid_primary_keys(conn):
    with conn.cursor() as cur:
        for table in EXPECTED_TABLES:
            cur.execute(f"""
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = 'id'
            """)
            row = cur.fetchone()
            assert row is not None, f"Table '{table}' missing 'id' column"
            assert row[0] == "uuid", f"Table '{table}' id is not UUID type"


def test_timestamps_exist(conn):
    tables_with_timestamps = [
        "empresas", "oficinas", "usuarios", "pedidos", "propostas",
        "producao", "pagamentos", "certificacoes",
    ]
    with conn.cursor() as cur:
        for table in tables_with_timestamps:
            cur.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table}'
                  AND column_name IN ('created_at', 'updated_at')
            """)
            cols = {row[0] for row in cur.fetchall()}
            assert "created_at" in cols, f"'{table}' missing created_at"
            assert "updated_at" in cols, f"'{table}' missing updated_at"


def test_soft_delete_columns(conn):
    tables_with_soft_delete = ["empresas", "oficinas", "usuarios", "pedidos"]
    with conn.cursor() as cur:
        for table in tables_with_soft_delete:
            cur.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = 'deleted_at'
            """)
            assert cur.fetchone() is not None, f"'{table}' missing deleted_at"


def test_enum_types_exist(conn):
    expected_enums = [
        "user_role", "empresa_size", "oficina_tier", "pedido_status",
        "proposta_status", "producao_status", "pagamento_status",
        "pagamento_metodo", "certificacao_tipo", "evento_tipo",
    ]
    with conn.cursor() as cur:
        cur.execute("""
            SELECT typname FROM pg_type WHERE typtype = 'e'
        """)
        existing_enums = {row[0] for row in cur.fetchall()}

    for enum in expected_enums:
        assert enum in existing_enums, f"ENUM '{enum}' not found"


def test_foreign_key_constraints(conn):
    with conn.cursor() as cur:
        # Pedidos must reference existing empresas
        cur.execute("""
            SELECT COUNT(*) FROM pedidos p
            LEFT JOIN empresas e ON p.empresa_id = e.id
            WHERE e.id IS NULL
        """)
        assert cur.fetchone()[0] == 0, "Pedidos with invalid empresa_id found"
