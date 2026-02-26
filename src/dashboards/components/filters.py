"""Sidebar filter widgets reused across dashboard pages."""

from datetime import date, timedelta

import streamlit as st


def date_range_filter(key_prefix: str = "dr") -> tuple[date, date]:
    """
    Render start / end date inputs in the sidebar.

    Returns (start_date, end_date).
    Defaults to last 12 months.
    """
    today = date.today()
    default_start = today.replace(year=today.year - 1)

    start = st.sidebar.date_input(
        "De",
        value=default_start,
        key=f"{key_prefix}_start",
    )
    end = st.sidebar.date_input(
        "Até",
        value=today,
        key=f"{key_prefix}_end",
    )
    return date(start.year, start.month, start.day), date(end.year, end.month, end.day)


def estado_filter(estados: list[str], key: str = "estado") -> list[str]:
    """
    Multiselect for Brazilian state codes.

    Returns list of selected estados (empty = all).
    """
    return st.sidebar.multiselect(
        "Estado(s)",
        options=sorted(estados),
        default=[],
        key=key,
        placeholder="Todos os estados",
    )


def segment_filter(segments: list[str], key: str = "segment") -> list[str]:
    """
    Multiselect for empresa segments.

    Returns list of selected segments (empty = all).
    """
    return st.sidebar.multiselect(
        "Segmento(s)",
        options=sorted(segments),
        default=[],
        key=key,
        placeholder="Todos os segmentos",
    )


def tier_filter(key: str = "tier") -> list[str]:
    """
    Multiselect for oficina tier levels.

    Returns list of selected tiers (empty = all).
    """
    all_tiers = ["elite", "premium", "standard", "basico"]
    return st.sidebar.multiselect(
        "Tier(s)",
        options=all_tiers,
        default=[],
        key=key,
        placeholder="Todos os tiers",
    )


def score_range_filter(key: str = "score") -> tuple[float, float]:
    """Slider for filtering by minimum / maximum score (0–10)."""
    return st.sidebar.slider(
        "Score mínimo / máximo",
        min_value=0.0,
        max_value=10.0,
        value=(0.0, 10.0),
        step=0.5,
        key=key,
    )
