"""
Tests for app initialization of MCP server references and Claude client pre-warm.
"""
from unittest.mock import MagicMock, patch

import pytest


class MockSessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


def test_init_mcp_and_ai_calls_setters_and_client_when_key_in_session():
    from sans_webapp import app

    mock_st = MagicMock()
    mock_st.session_state = MockSessionState()
    mock_st.session_state.fitter = "FAKE_FITTER"
    mock_st.session_state.chat_api_key = "TEST_KEY"

    with patch.object(app, 'st', mock_st):
        with patch('sans_webapp.mcp_server.set_fitter') as mock_set_fitter, patch(
            'sans_webapp.mcp_server.set_state_accessor'
        ) as mock_set_accessor, patch(
            'sans_webapp.services.claude_mcp_client.get_claude_client'
        ) as mock_get_client:
            app.init_mcp_and_ai()

            mock_set_fitter.assert_called_once_with("FAKE_FITTER")
            mock_set_accessor.assert_called_once_with(mock_st.session_state)
            mock_get_client.assert_called_once_with("TEST_KEY")


def test_init_mcp_and_ai_calls_setters_but_not_client_when_no_key():
    from sans_webapp import app

    mock_st = MagicMock()
    mock_st.session_state = MockSessionState()
    mock_st.session_state.fitter = "FAKE_FITTER"

    with patch.object(app, 'st', mock_st):
        with patch('sans_webapp.mcp_server.set_fitter') as mock_set_fitter, patch(
            'sans_webapp.mcp_server.set_state_accessor'
        ) as mock_set_accessor, patch(
            'sans_webapp.services.claude_mcp_client.get_claude_client'
        ) as mock_get_client:
            app.init_mcp_and_ai()

            mock_set_fitter.assert_called_once_with("FAKE_FITTER")
            mock_set_accessor.assert_called_once_with(mock_st.session_state)
            mock_get_client.assert_not_called()


def test_init_mcp_and_ai_client_error_stored_in_session_state():
    from sans_webapp import app

    mock_st = MagicMock()
    mock_st.session_state = MockSessionState()
    mock_st.session_state.fitter = "FAKE_FITTER"
    mock_st.session_state.chat_api_key = "BAD_KEY"

    with patch.object(app, 'st', mock_st):
        with patch('sans_webapp.mcp_server.set_fitter'), patch(
            'sans_webapp.mcp_server.set_state_accessor'
        ), patch('sans_webapp.services.claude_mcp_client.get_claude_client', side_effect=ValueError('bad key')):
            app.init_mcp_and_ai()

            assert 'ai_client_error' in mock_st.session_state
            assert 'bad key' in mock_st.session_state['ai_client_error']
