"""
Texlink Analytics — Seed Loader
=================================
Loads generated seed data into PostgreSQL using psycopg2.
Uses COPY for high-throughput inserts with proper error handling.
"""

from __future__ import annotations

import csv
import io
import os
import sys
from dataclasses import fields as dataclass_fields
from datetime import date, datetime
from typing import Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from loguru import logger

from src.seeds.seed_generator import TexlinkDataset, TexlinkSeeder, load_config

load_dotenv()

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_connection() -> psycopg2.extensions.connection:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        host = os.getenv("PGHOST", "localhost")
        port = os.getenv("PGPORT", "5432")
        db   = os.getenv("PGDATABASE", "texlink")
        user = os.getenv("PGUSER", "texlink")
        pwd  = os.getenv("PGPASSWORD", "password")
        db_url = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
    logger.info(f"Connecting to database...")
    return psycopg2.connect(db_url)


# ---------------------------------------------------------------------------
# Serializer: dict → CSV-compatible row
# ---------------------------------------------------------------------------

def _serialize_value(v: Any) -> str:
    """Convert Python value to PostgreSQL-safe CSV string."""
    if v is None:
        return r"\N"
    if isinstance(v, bool):
        return "t" if v else "f"
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, list):
        # PostgreSQL array literal: {"val1","val2"}
        escaped = [str(item).replace('"', '\\"') for item in v]
        return "{" + ",".join(f'"{e}"' for e in escaped) + "}"
    # Escape characters that break PostgreSQL COPY TEXT format
    s = str(v)
    s = s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
    return s


def dicts_to_tsv(rows: list[dict]) -> io.StringIO:
    """Convert list of dicts to tab-separated values buffer for COPY."""
    if not rows:
        return io.StringIO()
    buf = io.StringIO()
    for row in rows:
        line = "\t".join(_serialize_value(v) for v in row.values())
        buf.write(line + "\n")
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Loaders per table
# ---------------------------------------------------------------------------

TABLE_COLUMN_ORDER: dict[str, list[str]] = {
    "categorias_produto": [
        "id", "nome", "slug", "descricao", "parent_id", "nivel", "ativo", "created_at", "updated_at",
    ],
    "empresas": [
        "id", "razao_social", "nome_fantasia", "cnpj", "email", "telefone", "website", "logo_url",
        "endereco", "cidade", "estado", "cep", "porte", "segmento", "volume_mensal", "descricao",
        "ativo", "verificado", "data_verificacao", "created_at", "updated_at", "deleted_at",
    ],
    "oficinas": [
        "id", "razao_social", "nome_fantasia", "cnpj", "email", "telefone", "responsavel", "logo_url",
        "endereco", "cidade", "estado", "cep", "num_costureiras", "capacidade_mensal",
        "especialidades", "maquinario", "tier", "score_qualidade", "score_pontualidade",
        "score_comunicacao", "total_avaliacoes", "ativo", "verificado", "data_verificacao",
        "created_at", "updated_at", "deleted_at",
    ],
    "usuarios": [
        "id", "email", "nome", "telefone", "role", "avatar_url", "empresa_id", "oficina_id",
        "ultimo_login", "login_count", "ativo", "created_at", "updated_at", "deleted_at",
    ],
    "pedidos": [
        "id", "codigo", "empresa_id", "oficina_id", "titulo", "descricao", "categoria_id",
        "quantidade_total", "unidade", "valor_estimado", "valor_final", "moeda",
        "data_publicacao", "data_limite_propostas", "prazo_entrega", "data_entrega_real",
        "status", "prioridade", "observacoes", "anexos_urls", "created_at", "updated_at", "deleted_at",
    ],
    "pedido_items": [
        "id", "pedido_id", "descricao", "quantidade", "tamanho", "cor", "material",
        "valor_unitario", "observacoes", "created_at",
    ],
    "propostas": [
        "id", "pedido_id", "oficina_id", "valor_proposto", "prazo_proposto", "descricao",
        "condicoes", "status", "data_resposta", "motivo_recusa", "created_at", "updated_at",
    ],
    "producao": [
        "id", "pedido_id", "oficina_id", "status", "percentual_concluido",
        "quantidade_produzida", "quantidade_aprovada", "quantidade_rejeitada",
        "data_inicio", "data_previsao", "data_conclusao", "observacoes_qualidade",
        "fotos_producao", "created_at", "updated_at",
    ],
    "avaliacoes": [
        "id", "pedido_id", "avaliador_id", "avaliado_empresa_id", "avaliado_oficina_id",
        "nota_geral", "nota_qualidade", "nota_pontualidade", "nota_comunicacao",
        "nota_custo_beneficio", "comentario", "publica", "created_at",
    ],
    "certificacoes": [
        "id", "oficina_id", "tipo", "nome", "entidade_emissora", "numero_certificado",
        "data_emissao", "data_validade", "ativo", "documento_url", "verificado",
        "data_verificacao", "created_at", "updated_at",
    ],
    "pagamentos": [
        "id", "pedido_id", "empresa_id", "oficina_id", "valor_bruto", "taxa_plataforma",
        "valor_liquido", "percentual_taxa", "metodo", "status", "referencia_externa",
        "comprovante_url", "data_vencimento", "data_pagamento", "created_at", "updated_at",
    ],
    "mensagens": [
        "id", "remetente_id", "destinatario_id", "pedido_id", "conteudo",
        "lida", "data_leitura", "created_at",
    ],
    "eventos_plataforma": [
        "id", "usuario_id", "session_id", "tipo", "pagina", "referrer",
        "entidade_tipo", "entidade_id", "metadata", "ip_address", "user_agent",
        "dispositivo", "created_at",
    ],
    "notificacoes": [
        "id", "usuario_id", "titulo", "conteudo", "tipo", "canal",
        "entidade_tipo", "entidade_id", "lida", "data_leitura", "created_at",
    ],
}

# Load order respects FK dependencies
LOAD_ORDER = [
    "categorias_produto",
    "empresas",
    "oficinas",
    "usuarios",
    "pedidos",
    "pedido_items",
    "propostas",
    "producao",
    "avaliacoes",
    "certificacoes",
    "pagamentos",
    "mensagens",
    "eventos_plataforma",
    "notificacoes",
]


def load_table(conn, table: str, rows: list[dict]) -> int:
    """Load rows into a PostgreSQL table using COPY."""
    if not rows:
        logger.warning(f"  Skipping {table} — no rows")
        return 0

    columns = TABLE_COLUMN_ORDER[table]

    # Reorder dict keys to match column order, fill missing with None
    ordered_rows = []
    for row in rows:
        ordered_rows.append({col: row.get(col) for col in columns})

    buf = dicts_to_tsv(ordered_rows)
    col_list = ", ".join(columns)

    with conn.cursor() as cur:
        cur.copy_expert(
            f"COPY {table} ({col_list}) FROM STDIN WITH (FORMAT text, NULL '\\N')",
            buf,
        )

    logger.info(f"  ✓ {table:<25} {len(rows):>6} rows loaded")
    return len(rows)


def load_all(conn, dataset: TexlinkDataset) -> dict[str, int]:
    """Load all tables in FK-safe order."""
    table_data_map = {
        "categorias_produto": dataset.categorias,
        "empresas": dataset.empresas,
        "oficinas": dataset.oficinas,
        "usuarios": dataset.usuarios,
        "pedidos": dataset.pedidos,
        "pedido_items": dataset.pedido_items,
        "propostas": dataset.propostas,
        "producao": dataset.producao,
        "avaliacoes": dataset.avaliacoes,
        "certificacoes": dataset.certificacoes,
        "pagamentos": dataset.pagamentos,
        "mensagens": dataset.mensagens,
        "eventos_plataforma": dataset.eventos_plataforma,
        "notificacoes": dataset.notificacoes,
    }

    totals = {}
    logger.info("Loading seed data into PostgreSQL...")
    logger.info("-" * 50)

    for table in LOAD_ORDER:
        rows = table_data_map.get(table, [])
        try:
            n = load_table(conn, table, rows)
            totals[table] = n
        except Exception as e:
            logger.error(f"  ✗ Failed loading {table}: {e}")
            conn.rollback()
            raise

    conn.commit()
    return totals


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_counts(conn, totals: dict[str, int]) -> bool:
    """Basic row count validation after load."""
    logger.info("\nValidating loaded data...")
    all_ok = True

    with conn.cursor() as cur:
        for table, expected in totals.items():
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cur.fetchone()[0]
            ok = actual >= expected
            symbol = "✓" if ok else "✗"
            logger.info(f"  {symbol} {table:<25} expected={expected} actual={actual}")
            if not ok:
                all_ok = False

    # Check referential integrity examples
    checks = [
        ("pedidos referencing valid empresas",
         "SELECT COUNT(*) FROM pedidos p LEFT JOIN empresas e ON p.empresa_id = e.id WHERE e.id IS NULL"),
        ("propostas with valid pedidos",
         "SELECT COUNT(*) FROM propostas pr LEFT JOIN pedidos p ON pr.pedido_id = p.id WHERE p.id IS NULL"),
        ("pagamentos with valid pedidos",
         "SELECT COUNT(*) FROM pagamentos pg LEFT JOIN pedidos p ON pg.pedido_id = p.id WHERE p.id IS NULL"),
    ]

    with conn.cursor() as cur:
        for desc, sql in checks:
            cur.execute(sql)
            orphans = cur.fetchone()[0]
            ok = orphans == 0
            symbol = "✓" if ok else "✗"
            logger.info(f"  {symbol} {desc}: {orphans} orphan(s)")
            if not ok:
                all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(config_path: str = "src/seeds/seed_config.yaml", truncate: bool = False) -> None:
    logger.info("=" * 60)
    logger.info("Texlink Seed Loader")
    logger.info("=" * 60)

    # Generate data
    cfg = load_config(config_path)
    seeder = TexlinkSeeder(cfg)
    dataset = seeder.generate_all()

    # Connect
    conn = get_connection()
    conn.autocommit = False

    try:
        if truncate:
            logger.warning("Truncating all tables (TRUNCATE CASCADE)...")
            with conn.cursor() as cur:
                for table in reversed(LOAD_ORDER):
                    cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            conn.commit()
            logger.info("Tables cleared.")

        # Load
        totals = load_all(conn, dataset)

        # Validate
        ok = validate_counts(conn, totals)

        if ok:
            logger.info("\n✅ Seed load complete and validated!")
        else:
            logger.warning("\n⚠️  Load complete but some validations failed. Check logs.")

    except Exception as e:
        logger.error(f"Load failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Load Texlink seed data into PostgreSQL")
    parser.add_argument("--config", default="src/seeds/seed_config.yaml")
    parser.add_argument("--truncate", action="store_true", help="Truncate tables before loading")
    args = parser.parse_args()
    main(config_path=args.config, truncate=args.truncate)
