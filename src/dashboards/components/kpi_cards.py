"""KPI card helpers — thin wrappers around st.metric."""

from typing import Optional

import streamlit as st


def kpi_card(
    label: str,
    value,
    delta=None,
    delta_suffix: str = "",
    fmt: str = "{:,.0f}",
) -> None:
    """
    Render a single KPI metric card.

    Parameters
    ----------
    label : str
        Metric label shown above the value.
    value : numeric or str
        The main metric value. If numeric and fmt provided, will be formatted.
    delta : numeric or None
        Period-over-period delta (positive = good, negative = bad).
    delta_suffix : str
        Appended to the delta string (e.g. "%" or " MoM").
    fmt : str
        Python format string for value (default: thousand-separated integer).
    """
    if value is None or (hasattr(value, "__float__") and __import__("math").isnan(float(value))):
        formatted_value = "—"
    elif isinstance(value, str):
        formatted_value = value
    else:
        try:
            formatted_value = fmt.format(value)
        except (ValueError, TypeError):
            formatted_value = str(value)

    delta_str: Optional[str] = None
    if delta is not None:
        try:
            sign = "+" if float(delta) >= 0 else ""
            delta_str = f"{sign}{delta:.1f}{delta_suffix}"
        except (ValueError, TypeError):
            delta_str = str(delta)

    st.metric(label=label, value=formatted_value, delta=delta_str)


def kpi_row(metrics: list[dict]) -> None:
    """
    Render a horizontal row of KPI cards.

    Each dict in metrics may contain:
        label, value, delta (optional), delta_suffix (optional), fmt (optional)
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            kpi_card(
                label=m["label"],
                value=m.get("value"),
                delta=m.get("delta"),
                delta_suffix=m.get("delta_suffix", ""),
                fmt=m.get("fmt", "{:,.0f}"),
            )
