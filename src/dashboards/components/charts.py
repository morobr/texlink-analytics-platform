"""
Chart factory functions for Texlink Analytics dashboards.

All functions return Plotly Figure or Altair Chart objects.
Callers render with st.plotly_chart / st.altair_chart.
"""

from typing import Optional

import altair as alt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Colour palette (Texlink brand-ish teal/blue) ─────────────────────────────
_PRIMARY = "#0077B6"
_SECONDARY = "#00B4D8"
_ACCENT = "#90E0EF"
_DANGER = "#EF476F"
_SUCCESS = "#06D6A0"
_PALETTE = [_PRIMARY, _SECONDARY, "#48CAE4", "#ADE8F4", _ACCENT]


def line_chart(
    df: pd.DataFrame,
    x: str,
    y_cols: list[str],
    title: str = "",
    y_label: str = "",
) -> go.Figure:
    """Multi-line time-series chart."""
    fig = go.Figure()
    colors = _PALETTE + px.colors.qualitative.Plotly
    for i, col in enumerate(y_cols):
        fig.add_trace(
            go.Scatter(
                x=df[x],
                y=df[col],
                mode="lines+markers",
                name=col,
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=5),
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title=x,
        yaxis_title=y_label,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="x unified",
    )
    return fig


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: Optional[str] = None,
    orientation: str = "v",
    color_map: Optional[dict] = None,
) -> go.Figure:
    """Vertical or horizontal bar chart."""
    kwargs = dict(
        data_frame=df,
        x=x if orientation == "v" else y,
        y=y if orientation == "v" else x,
        title=title,
        orientation=orientation,
        color=color,
        color_discrete_map=color_map or {},
        color_discrete_sequence=_PALETTE,
        height=380,
    )
    fig = px.bar(**{k: v for k, v in kwargs.items() if v is not None or k in ("x", "y", "title", "orientation", "height", "data_frame")})
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def funnel_chart(
    stages: list[str],
    counts: list[int],
    title: str = "Funil de Conversão",
) -> go.Figure:
    """Plotly Funnel chart for conversion funnels."""
    fig = go.Figure(
        go.Funnel(
            y=stages,
            x=counts,
            textinfo="value+percent initial",
            marker=dict(color=_PALETTE[:len(stages)] if len(stages) <= len(_PALETTE) else None),
        )
    )
    fig.update_layout(title=title, height=400, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def cohort_heatmap(matrix: pd.DataFrame, title: str = "Retenção por Cohort") -> alt.Chart:
    """
    Altair heatmap for cohort retention matrices.

    matrix: rows = cohort label, columns = mes_n (0, 1, 2, …)
    """
    melted = matrix.reset_index().melt(id_vars=matrix.index.name or "index")
    melted.columns = ["cohort", "mes_n", "retencao"]
    melted["mes_n"] = melted["mes_n"].astype(str)

    chart = (
        alt.Chart(melted)
        .mark_rect()
        .encode(
            x=alt.X("mes_n:O", title="Mês desde cadastro"),
            y=alt.Y("cohort:O", title="Cohort"),
            color=alt.Color(
                "retencao:Q",
                scale=alt.Scale(scheme="blues", domain=[0, 100]),
                title="Retenção %",
            ),
            tooltip=["cohort", "mes_n", alt.Tooltip("retencao:Q", format=".1f")],
        )
        .properties(title=title, height=300)
    )

    text = chart.mark_text(baseline="middle", fontSize=10).encode(
        text=alt.Text("retencao:Q", format=".0f"),
        color=alt.condition(
            alt.datum.retencao > 50,
            alt.value("white"),
            alt.value("black"),
        ),
    )
    return chart + text


def scatter_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: Optional[str] = None,
    size: Optional[str] = None,
    title: str = "",
    hover_name: Optional[str] = None,
) -> go.Figure:
    """Scatter / bubble chart using Plotly Express."""
    fig = px.scatter(
        df,
        x=x,
        y=y,
        color=color,
        size=size,
        title=title,
        hover_name=hover_name,
        color_discrete_sequence=_PALETTE,
        height=420,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def donut_chart(
    df: pd.DataFrame,
    names: str,
    values: str,
    title: str = "",
) -> go.Figure:
    """Donut (pie with hole) chart."""
    fig = px.pie(
        df,
        names=names,
        values=values,
        title=title,
        hole=0.45,
        color_discrete_sequence=_PALETTE,
        height=380,
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def dual_axis_line_chart(
    df: pd.DataFrame,
    x: str,
    y1: str,
    y2: str,
    y1_label: str = "",
    y2_label: str = "",
    title: str = "",
) -> go.Figure:
    """Line chart with two y-axes (e.g. GMV + Revenue)."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df[x], y=df[y1], name=y1_label or y1,
            mode="lines+markers", line=dict(color=_PRIMARY, width=2), yaxis="y1",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df[x], y=df[y2], name=y2_label or y2,
            mode="lines+markers", line=dict(color=_SECONDARY, width=2, dash="dash"), yaxis="y2",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=x,
        yaxis=dict(title=y1_label or y1, side="left"),
        yaxis2=dict(title=y2_label or y2, side="right", overlaying="y"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig
