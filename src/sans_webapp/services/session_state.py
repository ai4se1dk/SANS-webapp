"""
Session state management for SANS webapp.

Centralizes all session state initialization and utility functions.
"""

import numpy as np
import streamlit as st
from sans_fitter import SANSFitter, examples

from sans_webapp.ui_constants import MAX_FLOAT_DISPLAY, MIN_FLOAT_DISPLAY


def init_session_state() -> None:
    """Initialize Streamlit session state with defaults."""
    defaults: dict[str, object] = {
        'fitter': SANSFitter,
        'data_loaded': False,
        'model_selected': False,
        'fit_completed': False,
        'fit_warnings': [],
        'show_ai_chat': False,
        'chat_api_key': None,
        'slider_value': 0.0,
        'prev_selected_param': None,
        'last_uploaded_file_id': None,
        # Sidebar expander states - only data_upload starts expanded
        'expand_data_upload': True,
        'expand_model_selection': False,
        'expand_fitting': False,
        # Main content expander states
        'expand_data_preview': True,
        'expand_parameters': True,
        # AI tools
        'ai_tools_enabled': False,
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default() if callable(default) else default


def clamp_for_display(value: float) -> float:
    """
    Clamp a value to a range that Streamlit's number_input can handle.
    Converts inf/-inf to displayable bounds.

    Args:
        value: The value to clamp

    Returns:
        The clamped value
    """
    if np.isinf(value):
        return MAX_FLOAT_DISPLAY if value > 0 else MIN_FLOAT_DISPLAY
    return value


def clear_parameter_state() -> None:
    """Clear all parameter-related session state keys."""
    keys_to_remove = [
        k
        for k in st.session_state.keys()
        if k.startswith('value_')
        or k.startswith('min_')
        or k.startswith('max_')
        or k.startswith('vary_')
        or k.startswith('pd_width_')
        or k.startswith('pd_n_')
        or k.startswith('pd_type_')
        or k.startswith('pd_vary_')
        or k == 'pd_enabled'
        or k == 'pd_updates'
        or k == 'param_updates'
    ]
    for key in keys_to_remove:
        del st.session_state[key]


def clear_q_range_state() -> None:
    """Clear the fit Q-range widget keys (call when a new dataset is loaded)."""
    for key in ('fit_qmin', 'fit_qmax'):
        if key in st.session_state:
            del st.session_state[key]


def adopt_fitter(fitter: SANSFitter) -> None:
    """
    Make *fitter* the app's fitter, replacing the current one.

    Used when a complete fitter arrives from elsewhere (a loaded analysis, an
    example). Clears the widget state that described the old fitter, so the
    parameter, polydispersity and Q-range widgets re-initialize from the new
    one, and sets the progress flags from what the new fitter holds. The MCP
    server picks the new fitter up on the next rerun (``init_mcp_and_ai``).

    Args:
        fitter: The fitter to use from now on
    """
    clear_parameter_state()
    clear_q_range_state()
    st.session_state.fitter = fitter
    st.session_state.data_loaded = fitter.data is not None
    st.session_state.model_selected = fitter.model_name is not None
    st.session_state.current_model = fitter.model_name
    st.session_state.fit_warnings = []
    if fitter.fit_result is None:
        st.session_state.fit_completed = False
        st.session_state.pop('fit_result', None)
    else:
        st.session_state.fit_completed = True
        st.session_state.fit_result = fitter.fit_result


def load_example(name: str) -> SANSFitter:
    """
    Replace the app's fitter with one of sans-fitter's bundled examples.

    The example comes with its data, model and suggested starting parameters
    (and any structure factor and polydispersity), ready to fit.

    Args:
        name: Example name, one of ``examples.list_examples()``

    Returns:
        The new fitter
    """
    fitter = examples.load_fitter(name)
    adopt_fitter(fitter)
    return fitter


def get_fitter() -> SANSFitter:
    """Get the fitter instance from session state."""
    return st.session_state.fitter


def is_data_loaded() -> bool:
    """Check if data is loaded."""
    return st.session_state.data_loaded


def is_model_selected() -> bool:
    """Check if a model is selected."""
    return st.session_state.model_selected


def is_fit_completed() -> bool:
    """Check if a fit has been completed."""
    return st.session_state.fit_completed


def get_api_key() -> str | None:
    """Get the stored API key."""
    return st.session_state.chat_api_key
