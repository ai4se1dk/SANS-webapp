"""
Parameter correlation component for SANS webapp.

Shows the correlation matrix of the last fit's free parameters as a heatmap.
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from sans_fitter import SANSFitter

from sans_webapp.ui_constants import (
    CORRELATIONS_CAPTION,
    CORRELATIONS_HEADER,
    CORRELATIONS_STRONG_WARNING,
)


def plot_correlation_matrix(labels: list[str], corr: np.ndarray) -> go.Figure:
    """
    Heatmap of a parameter correlation matrix (strict lower triangle).

    Styled like sans-fitter's posterior correlation plot, which only covers
    Bayesian fits: a diverging red/blue scale fixed to [-1, 1], so strongly
    (anti-)correlated pairs stand out whatever the matrix.

    Args:
        labels: Parameter names, in matrix order
        corr: Square correlation matrix

    Returns:
        Plotly figure object
    """
    display = np.array(corr, dtype=float)
    display[np.triu_indices_from(display)] = np.nan
    # The first row and last column hold no lower-triangle cells: drop them
    display = display[1:, :-1]
    text = np.where(np.isnan(display), '', np.char.mod('%.2f', np.nan_to_num(display)))

    fig = go.Figure(
        go.Heatmap(
            z=display,
            x=labels[:-1],
            y=labels[1:],
            zmin=-1,
            zmax=1,
            colorscale='RdBu',
            reversescale=True,
            text=text,
            texttemplate='%{text}',
            colorbar={'title': 'ρ'},
            hoverongaps=False,
            hovertemplate='%{y} / %{x}: ρ = %{z:.3f}<extra></extra>',
        )
    )
    fig.update_layout(
        title='Parameter correlations',
        template='plotly_white',
        height=max(90 * (len(labels) - 1), 350),
        yaxis={'autorange': 'reversed'},
    )
    return fig


def render_parameter_correlations(fitter: SANSFitter) -> None:
    """Render the correlation matrix of the last fit's free parameters as a heatmap."""
    try:
        report = fitter.get_fit_report()
    except Exception:
        # No fit in this session (e.g. result restored without a contract)
        return
    corr = report.corr
    if corr is None or len(report.cov_labels) < 2:
        return

    pairs = report.strongly_correlated()
    with st.expander(CORRELATIONS_HEADER, expanded=bool(pairs)):
        st.caption(CORRELATIONS_CAPTION.format(source=report.cov_source or 'covariance'))
        for name_a, name_b, rho in pairs:
            st.warning(CORRELATIONS_STRONG_WARNING.format(a=name_a, b=name_b, rho=rho))
        fig = plot_correlation_matrix(list(report.cov_labels), corr)
        st.plotly_chart(fig, width='stretch', key='correlations_chart')
