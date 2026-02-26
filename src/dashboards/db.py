"""
DB connection helper for Streamlit dashboards.

Provides a cached SQLAlchemy engine and a query runner.
All pages import from here — never create engines directly in pages.
"""

import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


@st.cache_resource
def get_engine():
    """Return a cached SQLAlchemy engine using DATABASE_URL env var."""
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://texlink:password@localhost:5432/texlink"
    )
    return create_engine(db_url, pool_pre_ping=True)


@st.cache_data(ttl=300)
def run_query(sql: str) -> pd.DataFrame:
    """
    Execute a SQL query and return results as a DataFrame.
    Cached for 5 minutes. Returns empty DataFrame on error.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn)
    except OperationalError:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def db_available() -> bool:
    """Return True if the database is reachable."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
