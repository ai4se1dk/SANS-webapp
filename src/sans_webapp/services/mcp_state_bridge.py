"""
Session-state bridge for MCP tools.

Provides typed accessors for Streamlit session state,
enabling MCP tools to safely access and modify application state.
"""

from typing import Any, Optional

import streamlit as st
from sans_fitter import SANSFitter


class SessionStateBridge:
    """
    Bridge between MCP tools and Streamlit session state.

    Provides type-safe accessors for the fitter and related state,
    with proper error handling for edge cases.
    """

    def __init__(self):
        """Initialize the bridge."""
        pass

    @property
    def session_state(self) -> Any:
        """Get the Streamlit session state object."""
        return st.session_state

    def get_fitter(self) -> SANSFitter:
        """
        Get the current SANSFitter instance.

        Returns:
            The SANSFitter instance from session state.

        Raises:
            RuntimeError: If fitter is not initialized.
        """
        if 'fitter' not in st.session_state:
            raise RuntimeError('Fitter not initialized. Please wait for app to load.')

        fitter = st.session_state.fitter
        if fitter is None:
            raise RuntimeError('Fitter is None. Please reload the application.')

        return fitter

    def has_fitter(self) -> bool:
        """Check if fitter is available."""
        return 'fitter' in st.session_state and st.session_state.fitter is not None

    def has_data(self) -> bool:
        """Check if data is loaded in the fitter."""
        if not self.has_fitter():
            return False
        fitter = st.session_state.fitter
        return hasattr(fitter, 'data') and fitter.data is not None

    def has_model(self) -> bool:
        """Check if a model is selected."""
        if not self.has_fitter():
            return False
        fitter = st.session_state.fitter
        return hasattr(fitter, 'model') and fitter.model is not None

    def get_current_model_name(self) -> Optional[str]:
        """Get the name of the current model, or None if not set."""
        return st.session_state.get('current_model', None)

    def is_model_selected(self) -> bool:
        """Check if model_selected flag is set."""
        return st.session_state.get('model_selected', False)

    def is_data_loaded(self) -> bool:
        """Check if data_loaded flag is set."""
        return st.session_state.get('data_loaded', False)

    def is_fit_completed(self) -> bool:
        """Check if fit_completed flag is set."""
        return st.session_state.get('fit_completed', False)

    def are_tools_enabled(self) -> bool:
        """Check if AI tools are enabled."""
        return st.session_state.get('ai_tools_enabled', False)

    def set_needs_rerun(self, value: bool = True) -> None:
        """Set the needs_rerun flag."""
        st.session_state.needs_rerun = value

    def get_needs_rerun(self) -> bool:
        """Get the needs_rerun flag."""
        return st.session_state.get('needs_rerun', False)

    def clear_needs_rerun(self) -> None:
        """Clear the needs_rerun flag."""
        st.session_state.needs_rerun = False

    # State setters for MCP tools

    def set_current_model(self, model_name: str) -> None:
        """Set the current model name in session state."""
        st.session_state.current_model = model_name

    def set_model_selected(self, value: bool = True) -> None:
        """Set the model_selected flag."""
        st.session_state.model_selected = value

    def set_fit_completed(self, value: bool = True) -> None:
        """Set the fit_completed flag."""
        st.session_state.fit_completed = value

    def set_fit_result(self, result: Any) -> None:
        """Set the fit result in session state."""
        st.session_state.fit_result = result

    def get_fit_result(self) -> Optional[Any]:
        """Get the fit result from session state."""
        return st.session_state.get('fit_result', None)

    # Fit status management

    def get_fit_status(self) -> str:
        """Get the current fit status."""
        return st.session_state.get('fit_status', 'idle')

    def set_fit_status(self, status: str) -> None:
        """
        Set the fit status.

        Args:
            status: One of 'idle', 'queued', 'running', 'completed', 'failed'
        """
        valid_statuses = {'idle', 'queued', 'running', 'completed', 'failed'}
        if status not in valid_statuses:
            raise ValueError(f'Invalid fit status: {status}. Must be one of {valid_statuses}')
        st.session_state.fit_status = status

    def get_fit_error(self) -> Optional[str]:
        """Get the fit error message, if any."""
        return st.session_state.get('fit_error', None)

    def set_fit_error(self, error: Optional[str]) -> None:
        """Set the fit error message."""
        st.session_state.fit_error = error

    # Chat history management

    def get_chat_history(self) -> list[dict[str, str]]:
        """Get the chat history."""
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        return st.session_state.chat_history

    def append_chat_message(self, role: str, content: str) -> None:
        """Append a message to chat history."""
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        st.session_state.chat_history.append({'role': role, 'content': content})

    def clear_chat_history(self) -> None:
        """Clear the chat history."""
        st.session_state.chat_history = []

    # API key management

    def get_api_key(self) -> Optional[str]:
        """Get the API key from session state."""
        return st.session_state.get('chat_api_key', None)

    def set_api_key(self, api_key: str) -> None:
        """Set the API key in session state."""
        st.session_state.chat_api_key = api_key

    # Parameter widget state management

    def clear_parameter_widgets(self) -> None:
        """Clear all parameter widget state (for model changes)."""
        keys_to_remove = [
            k
            for k in st.session_state.keys()
            if k.startswith('value_')
            or k.startswith('min_')
            or k.startswith('max_')
            or k.startswith('vary_')
        ]
        for key in keys_to_remove:
            del st.session_state[key]


# Singleton instance
_bridge: Optional[SessionStateBridge] = None


def get_state_bridge() -> SessionStateBridge:
    """Get the singleton SessionStateBridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = SessionStateBridge()
    return _bridge


def get_fitter() -> SANSFitter:
    """Convenience function to get the fitter from the bridge."""
    return get_state_bridge().get_fitter()


def check_preconditions(
    require_data: bool = False, require_model: bool = False
) -> tuple[bool, str]:
    """
    Check preconditions for tool execution.

    Args:
        require_data: Whether data must be loaded
        require_model: Whether a model must be selected

    Returns:
        Tuple of (success, error_message)
    """
    bridge = get_state_bridge()

    if not bridge.has_fitter():
        return False, 'Fitter not initialized. Please wait for app to load.'

    if require_data and not bridge.has_data():
        return False, 'No data loaded. Please load data first.'

    if require_model and not bridge.has_model():
        return False, 'No model selected. Please select a model first.'

    return True, ''


def check_tools_enabled() -> tuple[bool, str]:
    """
    Check if AI tools are enabled.

    Returns:
        Tuple of (enabled, message)
    """
    bridge = get_state_bridge()

    if not bridge.are_tools_enabled():
        return False, 'AI tools are disabled. Enable them in the sidebar to allow modifications.'

    return True, ''
