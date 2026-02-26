"""
Texlink Analytics — Model Runner
==================================
Executes all SQL models in dependency order against the configured PostgreSQL database.
Creates views for each model layer: staging → intermediate → marts
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ---------------------------------------------------------------------------
# Model execution order (respects dependencies)
# ---------------------------------------------------------------------------

EXECUTION_PLAN = [
    # Layer 1: Staging
    ("staging", [
        "stg_empresas",
        "stg_oficinas",
        "stg_usuarios",
        "stg_pedidos",
        "stg_pedido_items",
        "stg_propostas",
        "stg_producao",
        "stg_avaliacoes",
        "stg_certificacoes",
        "stg_pagamentos",
        "stg_eventos_plataforma",
    ]),
    # Layer 2: Intermediate
    ("intermediate", [
        "int_pedidos_enriched",
        "int_oficina_performance",
        "int_empresa_activity",
        "int_funnel_stages",
        "int_match_pairs",
        "int_daily_platform_snapshot",
    ]),
    # Layer 3: Marts
    ("marts", [
        "marts_platform_kpis",
        "marts_customer_journey",
        "marts_cohort_analysis",
        "marts_oficina_scoring",
        "marts_empresa_clv",
        "marts_match_quality",
        "marts_revenue_analytics",
        "marts_geographic_analysis",
    ]),
]

MODELS_BASE = Path(__file__).parent


def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        host = os.getenv("PGHOST", "localhost")
        port = os.getenv("PGPORT", "5432")
        db   = os.getenv("PGDATABASE", "texlink")
        user = os.getenv("PGUSER", "texlink")
        pwd  = os.getenv("PGPASSWORD", "password")
        db_url = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
    return psycopg2.connect(db_url)


def run_model(conn, layer: str, model_name: str) -> None:
    sql_path = MODELS_BASE / layer / f"{model_name}.sql"
    if not sql_path.exists():
        logger.warning(f"  Model file not found: {sql_path}")
        return

    sql = sql_path.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    logger.info(f"  ✓ {model_name}")


def run_all(conn) -> None:
    logger.info("=" * 60)
    logger.info("Texlink Analytics — Running all models")
    logger.info("=" * 60)

    total = 0
    for layer, models in EXECUTION_PLAN:
        logger.info(f"\nLayer: {layer.upper()}")
        for model_name in models:
            try:
                run_model(conn, layer, model_name)
                total += 1
            except Exception as e:
                logger.error(f"  ✗ {model_name}: {e}")
                conn.rollback()
                raise

    conn.commit()
    logger.info(f"\n✅ {total} models executed successfully")


def main():
    conn = get_connection()
    conn.autocommit = False
    try:
        run_all(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
