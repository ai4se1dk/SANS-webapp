"""
Session state management for SANS webapp.

Centralizes all session state initialization and utility functions.
"""

import numpy as np
import streamlit as st
from sans_fitter import SANSFitter

from sans_webapp.ui_constants import MAX_FLOAT_DISPLAY, MIN_FLOAT_DISPLAY


def init_session_state() -> None:
    """Initialize Streamlit session state with defaults."""
    defaults: dict[str, object] = {
        'fitter': SANSFitter,
        'data_loaded': False,
        'model_selected': False,
        'fit_completed': False,
        'show_ai_chat': False,
        'chat_api_key': None,
        'slider_value': 0.0,
        'prev_selected_param': None,
        'last_uploaded_file_id': None,
        # Sidebar expander states - only data_upload starts expanded
        'expand_data_upload': True,
        'expand_model_selection': False,
        'expand_fitting': False,
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
    ]
    for key in keys_to_remove:
        del st.session_state[key]


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
