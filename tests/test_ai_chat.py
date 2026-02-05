"""
Unit tests for AI chat service with Claude MCP integration.

Tests the modified ai_chat.py from Step 5.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Any
import numpy as np


class MockSessionState:
    """Mock for Streamlit session_state."""
    
    def __init__(self):
        self._data = {
            'ai_tools_enabled': True,
            'needs_rerun': False,
            'current_model': 'sphere',
            'model_selected': True,
            'data_loaded': True,
            'fit_completed': False,
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
        self.data.x = np.array([0.01, 0.02, 0.03])
        self.data.y = np.array([100.0, 50.0, 25.0])
        self.params = {
            'radius': MagicMock(value=50.0),
            'sld': MagicMock(value=1e-6),
        }


@pytest.fixture
def mock_fitter():
    """Create a mock fitter."""
    return MockFitter()


# =============================================================================
# Test _build_context
# =============================================================================


class TestBuildContext:
    """Test the context building for AI chat."""
    
    def test_build_context_includes_model(self, mock_fitter):
        """Context should include model information."""
        from sans_webapp.services.ai_chat import _build_context
        
        context = _build_context(mock_fitter)
        
        assert 'sphere' in context.lower() or 'model' in context.lower()
    
    def test_build_context_includes_parameters(self, mock_fitter):
        """Context should include parameter information."""
        from sans_webapp.services.ai_chat import _build_context
        
        context = _build_context(mock_fitter)
        
        assert 'radius' in context.lower() or 'parameter' in context.lower()
    
    def test_build_context_handles_none_fitter(self):
        """Context should handle None fitter gracefully."""
        from sans_webapp.services.ai_chat import _build_context
        
        context = _build_context(None)
        
        # Should return some default context or empty string
        assert isinstance(context, str)


# =============================================================================
# Test suggest_models_ai
# =============================================================================


class TestSuggestModelsAI:
    """Test the AI model suggestion function."""
    
    def test_suggest_models_requires_api_key(self):
        """suggest_models_ai should handle missing API key."""
        from sans_webapp.services.ai_chat import suggest_models_ai
        
        result = suggest_models_ai([0.01, 0.02], [100.0, 50.0], None)
        
        # Should return empty list or handle gracefully
        assert result is None or result == [] or isinstance(result, list)
    
    def test_suggest_models_with_data(self):
        """suggest_models_ai should return suggestions with valid input."""
        from sans_webapp.services.ai_chat import suggest_models_ai
        
        with patch('sans_webapp.services.ai_chat.get_claude_client') as mock_client:
            # Mock the Claude client
            mock_claude = MagicMock()
            mock_claude.simple_chat.return_value = "sphere\ncylinder\nellipsoid"
            mock_client.return_value = mock_claude
            
            result = suggest_models_ai(
                [0.01, 0.02, 0.03],
                [100.0, 50.0, 25.0],
                'fake-api-key'
            )
            
            # Should return a list of model suggestions
            assert isinstance(result, list)


# =============================================================================
# Test send_chat_message
# =============================================================================


class TestSendChatMessage:
    """Test the main chat message function."""
    
    def test_send_chat_message_returns_string(self, mock_fitter):
        """send_chat_message should return a string response."""
        from sans_webapp.services.ai_chat import send_chat_message
        
        with patch('sans_webapp.services.ai_chat.get_claude_client') as mock_get_client:
            with patch('sans_webapp.services.ai_chat.st') as mock_st:
                mock_st.session_state = MockSessionState()
                
                mock_client = MagicMock()
                mock_client.simple_chat.return_value = "Hello! How can I help?"
                mock_get_client.return_value = mock_client
                
                result = send_chat_message("Hello", "fake-api-key", mock_fitter)
                
                assert isinstance(result, str)
                assert len(result) > 0
    
    def test_send_chat_message_handles_error(self, mock_fitter):
        """send_chat_message should handle errors gracefully."""
        from sans_webapp.services.ai_chat import send_chat_message
        
        with patch('sans_webapp.services.ai_chat.get_claude_client') as mock_get_client:
            with patch('sans_webapp.services.ai_chat.st') as mock_st:
                mock_st.session_state = MockSessionState()
                
                mock_get_client.side_effect = Exception("API error")
                
                result = send_chat_message("Hello", "fake-api-key", mock_fitter)
                
                # Should return error message, not raise
                assert isinstance(result, str)
                assert 'error' in result.lower()

    def test_prompt_user_to_enable_tools_for_mutation_requests(self, mock_fitter):
        """If tools are disabled and user requests a state change, prompt to enable them."""
        from sans_webapp.services.ai_chat import send_chat_message

        with patch('sans_webapp.services.ai_chat.get_claude_client') as mock_get_client:
            with patch('sans_webapp.services.ai_chat.st') as mock_st:
                # Simulate tools disabled
                mock_st.session_state = MockSessionState()
                mock_st.session_state.ai_tools_enabled = False

                response = send_chat_message("Change sld to 2.0", "fake-api-key", mock_fitter)

                assert isinstance(response, str)
                assert 'enable' in response.lower() and 'ai tools' in response.lower()

    def test_response_requests_enable_tools_helper(self):
        """response_requests_enable_tools should detect the enable prompt in assistant text."""
        from sans_webapp.services.ai_chat import response_requests_enable_tools

        positive = "I can make that change automatically if you enable 'AI Tools' in the sidebar (🔧 Enable AI Tools)."
        negative = "I recommend setting the parameter to 2.0 using the UI."

        assert response_requests_enable_tools(positive) is True
        assert response_requests_enable_tools(negative) is False


# =============================================================================
# Test send_chat_message_with_tools
# =============================================================================


class TestSendChatMessageWithTools:
    """Test the tool-enabled chat function."""
    
    def test_returns_response_and_tools_invoked(self, mock_fitter):
        """Should return both response and tool invocation info."""
        from sans_webapp.services.ai_chat import send_chat_message_with_tools
        
        with patch('sans_webapp.services.ai_chat.get_claude_client') as mock_get_client:
            with patch('sans_webapp.services.ai_chat.st') as mock_st:
                mock_st.session_state = MockSessionState()
                
                mock_client = MagicMock()
                mock_client.chat.return_value = ("Response text", [{"tool_name": "set-model"}])
                mock_get_client.return_value = mock_client
                
                response, tools_invoked, needs_rerun = send_chat_message_with_tools(
                    "Use sphere model",
                    "fake-api-key",
                    mock_fitter
                )
                
                assert isinstance(response, str)
                assert isinstance(tools_invoked, list)


# =============================================================================
# Test _ensure_mcp_initialized
# =============================================================================


class TestEnsureMCPInitialized:
    """Test the MCP initialization function."""
    
    def test_initializes_mcp_server(self, mock_fitter):
        """Should initialize MCP server with fitter."""
        from sans_webapp.services.ai_chat import _ensure_mcp_initialized
        
        with patch('sans_webapp.services.ai_chat.set_fitter') as mock_set_fitter:
            with patch('sans_webapp.services.ai_chat.set_state_accessor') as mock_set_accessor:
                with patch('sans_webapp.services.ai_chat.st') as mock_st:
                    mock_st.session_state = MockSessionState()
                    
                    _ensure_mcp_initialized(mock_fitter)
                    
                    mock_set_fitter.assert_called_once_with(mock_fitter)
                    mock_set_accessor.assert_called_once()
