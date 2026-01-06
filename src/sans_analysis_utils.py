"""
SANS Data Analysis Utility Functions

Shared utility functions for SANS data analysis that can be used by both
the Streamlit web application and command-line scripts without importing Streamlit.
"""

from typing import Optional

import numpy as np
import plotly.graph_objects as go
from sans_fitter import SANSFitter
from sasmodels import core


def get_all_models() -> list[str]:
    """
    Fetch all available models from sasmodels.

    Returns:
        List of model names
    """
    try:
        all_models = core.list_models()
        return sorted(all_models)
    except Exception as e:
        print(f'Error fetching models: {str(e)}')
        return []


def analyze_data_for_ai_suggestion(q_data: np.ndarray, i_data: np.ndarray) -> str:
    """
    Analyze SANS data to create a description for AI model suggestion.

    Args:
        q_data: Q values (scattering vector)
        i_data: Intensity values

    Returns:
        String description of the data characteristics
    """
    # Calculate key features
    log_i = np.log10(i_data + 1e-10)  # Avoid log(0)
    log_q = np.log10(q_data + 1e-10)

    # Slope in log-log space (power law exponent)
    slope = np.polyfit(log_q, log_i, 1)[0]

    # Intensity ratio (high Q to low Q)
    low_q_intensity = np.mean(i_data[: len(i_data) // 10])
    high_q_intensity = np.mean(i_data[-len(i_data) // 10 :])
    intensity_ratio = low_q_intensity / (high_q_intensity + 1e-10)

    # Q range
    q_min, q_max = q_data.min(), q_data.max()

    description = f"""Data Analysis:
- Q range: {q_min:.4f} to {q_max:.4f} Å⁻¹
- Power law slope: {slope:.2f}
- Intensity decay: {intensity_ratio:.1f}x from low to high Q
- Data points: {len(q_data)}
"""
    return description


def suggest_models_simple(q_data: np.ndarray, i_data: np.ndarray) -> list[str]:
    """
    Simple heuristic-based model suggestion.

    This is a placeholder for AI-based suggestion. Based on data characteristics,
    suggests appropriate SANS models.

    Args:
        q_data: Q values
        i_data: Intensity values

    Returns:
        List of suggested model names
    """
    log_i = np.log10(i_data + 1e-10)
    log_q = np.log10(q_data + 1e-10)

    # Calculate slope
    slope = np.polyfit(log_q, log_i, 1)[0]

    suggestions = []

    # Heuristic rules based on slope and shape
    if slope < -3.5:
        # Steep decay - likely spherical particles
        suggestions = ['sphere', 'core_shell_sphere', 'fuzzy_sphere']
    elif -3.5 <= slope < -2:
        # Moderate decay - could be cylindrical or ellipsoidal
        suggestions = ['cylinder', 'ellipsoid', 'core_shell_cylinder']
    elif -2 <= slope < -1:
        # Gentle decay - possibly flat structures or aggregates
        suggestions = ['parallelepiped', 'lamellar', 'flexible_cylinder']
    else:
        # Flat or increasing - unusual, suggest common models
        suggestions = ['sphere', 'cylinder', 'ellipsoid']

    return suggestions[:5]  # Return top 5 suggestions


def plot_data_and_fit(
    fitter: SANSFitter,
    show_fit: bool = False,
    fit_q: Optional[np.ndarray] = None,
    fit_i: Optional[np.ndarray] = None,
) -> go.Figure:
    """
    Create an interactive Plotly figure with data and optionally fitted curve.

    Args:
        fitter: SANSFitter instance with loaded data
        show_fit: Whether to show fitted curve
        fit_q: Q values for fitted curve
        fit_i: Intensity values for fitted curve

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    # Plot original data with error bars
    fig.add_trace(
        go.Scatter(
            x=fitter.data.x,
            y=fitter.data.y,
            error_y={'type': 'data', 'array': fitter.data.dy, 'visible': True},
            mode='markers',
            name='Data',
            marker={'size': 6, 'color': 'blue', 'symbol': 'circle'},
        )
    )

    # Plot fitted curve if available
    if show_fit and fit_q is not None and fit_i is not None:
        fig.add_trace(
            go.Scatter(
                x=fit_q,
                y=fit_i,
                mode='lines',
                name='Fitted Model',
                line={'color': 'red', 'width': 2},
            )
        )

    # Update layout
    fig.update_layout(
        title='SANS Data Analysis',
        xaxis_title='Q (Å⁻¹)',
        yaxis_title='Intensity (cm⁻¹)',
        xaxis_type='log',
        yaxis_type='log',
        hovermode='closest',
        template='plotly_white',
        height=600,
        showlegend=True,
    )

    return fig
