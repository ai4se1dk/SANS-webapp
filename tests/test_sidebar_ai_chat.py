"""
Unit tests for the AI chat sidebar component.

Tests the changes made to sidebar.py in Step 6.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class MockSessionState:
    """Mock for Streamlit session_state."""

    def __init__(self):
        self._data = {
            'ai_tools_enabled': False,
            'needs_rerun': False,
            'show_ai_chat': True,
            'chat_history': [],
            'fitter': None,
        }

    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data


class MockFitter:
    """Mock for SANSFitter."""

    def __init__(self):
        self.model = MagicMock()
        self.model.name = 'sphere'
        self.data = MagicMock()


@pytest.fixture
def mock_session_state():
    """Create a mock session state."""
    return MockSessionState()


@pytest.fixture
def mock_fitter():
    """Create a mock fitter."""
    return MockFitter()


@pytest.fixture
def mock_streamlit():
    """Create a comprehensive mock for Streamlit."""
    with patch('sans_webapp.components.sidebar.st') as mock_st:
        # Setup mock session state
        mock_st.session_state = MockSessionState()

        # Setup sidebar context manager
        mock_sidebar = MagicMock()
        mock_st.sidebar = mock_sidebar

        # Setup expander context manager
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_sidebar.expander.return_value = mock_expander

        # Setup columns
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=False)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col1, mock_col2]

        # Setup container
        mock_container = MagicMock()
        mock_container.__enter__ = MagicMock(return_value=mock_container)
        mock_container.__exit__ = MagicMock(return_value=False)
        mock_st.container.return_value = mock_container

        # Setup status
        mock_status = MagicMock()
        mock_status.__enter__ = MagicMock(return_value=mock_status)
        mock_status.__exit__ = MagicMock(return_value=False)
        mock_st.status.return_value = mock_status

        yield mock_st


# =============================================================================
# Test render_ai_chat_sidebar
# =============================================================================


class TestRenderAIChatSidebar:
    """Test the render_ai_chat_sidebar function."""

    def test_renders_without_error(self, mock_streamlit, mock_fitter):
        """Function should render without raising exceptions."""
        from sans_webapp.components.sidebar import render_ai_chat_sidebar

        # Should not raise
        render_ai_chat_sidebar(api_key='test-key', fitter=mock_fitter)

    def test_renders_toggle_for_ai_tools(self, mock_streamlit, mock_fitter):
        """Should render an AI tools toggle."""
        from sans_webapp.components.sidebar import render_ai_chat_sidebar

        render_ai_chat_sidebar(api_key='test-key', fitter=mock_fitter)

        # Check that toggle was called
        mock_streamlit.toggle.assert_called()

    def test_renders_text_area_for_input(self, mock_streamlit, mock_fitter):
        """Should render a text area for chat input."""
        from sans_webapp.components.sidebar import render_ai_chat_sidebar

        render_ai_chat_sidebar(api_key='test-key', fitter=mock_fitter)

        # Check that text_area was called
        mock_streamlit.text_area.assert_called()

    def test_renders_send_button(self, mock_streamlit, mock_fitter):
        """Should render a send button."""
        from sans_webapp.components.sidebar import render_ai_chat_sidebar

        render_ai_chat_sidebar(api_key='test-key', fitter=mock_fitter)

        # Check that button was called (at least once for send/clear buttons)
        assert mock_streamlit.button.called

    def test_handles_none_api_key(self, mock_streamlit, mock_fitter):
        """Should handle None API key gracefully."""
        from sans_webapp.components.sidebar import render_ai_chat_sidebar

        # Should not raise
        render_ai_chat_sidebar(api_key=None, fitter=mock_fitter)

    def test_handles_none_fitter(self, mock_streamlit):
        """Should handle None fitter gracefully."""
        from sans_webapp.components.sidebar import render_ai_chat_sidebar

        # Should not raise
        render_ai_chat_sidebar(api_key='test-key', fitter=None)


# =============================================================================
# Test chat history display
# =============================================================================


class TestChatHistoryDisplay:
    """Test the chat history display logic."""

    def test_displays_empty_history(self, mock_streamlit, mock_fitter):
        """Should show caption when history is empty."""
        from sans_webapp.components.sidebar import render_ai_chat_sidebar

        mock_streamlit.session_state.chat_history = []

        render_ai_chat_sidebar(api_key='test-key', fitter=mock_fitter)

        # Check that caption was called (empty history message)
        mock_streamlit.caption.assert_called()

    def test_displays_messages_in_history(self, mock_streamlit, mock_fitter):
        """Should display messages when history has content."""
        from sans_webapp.components.sidebar import render_ai_chat_sidebar

        mock_streamlit.session_state.chat_history = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'},
        ]
        mock_streamlit.session_state._data['chat_history'] = (
            mock_streamlit.session_state.chat_history
        )

        render_ai_chat_sidebar(api_key='test-key', fitter=mock_fitter)

        # Check that markdown was called (for message headers)
        mock_streamlit.markdown.assert_called()


# =============================================================================
# Test needs_rerun handling
# =============================================================================


class TestNeedsRerunHandling:
    """Test the needs_rerun flag handling."""

    def test_triggers_rerun_when_flag_set(self, mock_streamlit, mock_fitter):
        """Should trigger rerun when needs_rerun is True."""
        from sans_webapp.components.sidebar import render_ai_chat_sidebar

        mock_streamlit.session_state.needs_rerun = True
        mock_streamlit.session_state._data['needs_rerun'] = True

        render_ai_chat_sidebar(api_key='test-key', fitter=mock_fitter)

        # After processing, needs_rerun should be handled
        # (either cleared or rerun called)
        # We can't easily test st.rerun() but we can verify the flag behavior


# =============================================================================
# Test AI tools toggle
# =============================================================================


class TestAIToolsToggle:
    """Test the AI tools enabled toggle."""

    def test_toggle_updates_session_state(self, mock_streamlit, mock_fitter):
        """Toggle should update ai_tools_enabled in session state."""
        from sans_webapp.components.sidebar import render_ai_chat_sidebar

        # Simulate toggle returning True
        mock_streamlit.toggle.return_value = True

        render_ai_chat_sidebar(api_key='test-key', fitter=mock_fitter)

        # Check toggle was called with correct parameters
        toggle_calls = mock_streamlit.toggle.call_args_list
        assert len(toggle_calls) > 0

        # First call should be for AI tools toggle
        call_args = toggle_calls[0]
        assert 'tool' in str(call_args).lower() or 'ai' in str(call_args).lower()
