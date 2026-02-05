"""
Unit tests for MCP server tools and related components.

Tests the MCP tools, Claude client, and session state bridge
created in Steps 1-7 of the MCP integration.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Any


# =============================================================================
# Test fixtures
# =============================================================================


class MockSessionState:
    """Mock for Streamlit session_state."""
    
    def __init__(self):
        self._data = {
            'ai_tools_enabled': True,
            'needs_rerun': False,
            'current_model': None,
            'model_selected': False,
            'data_loaded': False,
            'fit_completed': False,
            'fit_status': 'idle',
            'fit_result': None,
            'fit_error': None,
            'chat_history': [],
            'chat_api_key': None,
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
    
    def keys(self):
        return self._data.keys()
    
    def __delitem__(self, key):
        del self._data[key]


class MockFitter:
    """Mock for SANSFitter."""
    
    def __init__(self):
        self.model = None
        self.data = None
        self.params = {}
        self.result = None
    
    def set_model(self, model_name: str):
        self.model = MagicMock()
        self.model.name = model_name
        self.params = {
            'radius': MagicMock(value=50.0, bounds=(1, 500), vary=True),
            'sld': MagicMock(value=1e-6, bounds=(0, 1e-5), vary=True),
            'sld_solvent': MagicMock(value=6e-6, bounds=(0, 1e-5), vary=False),
            'background': MagicMock(value=0.001, bounds=(0, 1), vary=True),
        }
    
    def fit(self):
        result = MagicMock()
        result.redchi = 1.5
        self.result = result
        return result


@pytest.fixture
def mock_session_state():
    """Create a mock session state."""
    return MockSessionState()


@pytest.fixture
def mock_fitter():
    """Create a mock fitter."""
    return MockFitter()


# =============================================================================
# Test MCP tool schemas
# =============================================================================


class TestMCPToolSchemas:
    """Test the MCP tool schema definitions."""
    
    def test_get_mcp_tool_schemas_returns_list(self):
        """Tool schemas should return a list."""
        from sans_webapp.services.claude_mcp_client import get_mcp_tool_schemas
        
        schemas = get_mcp_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) == 11  # 11 tools defined
    
    def test_all_tools_have_required_fields(self):
        """Each tool schema should have name, description, and input_schema."""
        from sans_webapp.services.claude_mcp_client import get_mcp_tool_schemas
        
        schemas = get_mcp_tool_schemas()
        for schema in schemas:
            assert 'name' in schema
            assert 'description' in schema
            assert 'input_schema' in schema
            assert 'type' in schema['input_schema']
            assert schema['input_schema']['type'] == 'object'
    
    def test_expected_tool_names_present(self):
        """All expected tool names should be present."""
        from sans_webapp.services.claude_mcp_client import get_mcp_tool_schemas
        
        expected_tools = [
            'list-sans-models',
            'get-model-parameters',
            'get-current-state',
            'get-fit-results',
            'set-model',
            'set-parameter',
            'set-multiple-parameters',
            'enable-polydispersity',
            'set-structure-factor',
            'remove-structure-factor',
            'run-fit',
        ]
        
        schemas = get_mcp_tool_schemas()
        tool_names = [s['name'] for s in schemas]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Tool '{expected}' not found in schemas"


# =============================================================================
# Test MCP server tools
# =============================================================================


class TestMCPServerTools:
    """Test the MCP server tool functions."""
    
    def test_list_sans_models(self):
        """list_sans_models should return available models."""
        from sans_webapp.mcp_server import list_sans_models
        
        with patch('sans_webapp.mcp_server.get_all_models') as mock_get_models:
            mock_get_models.return_value = ['sphere', 'cylinder', 'ellipsoid']
            
            result = list_sans_models()
            
            assert 'sphere' in result
            assert 'cylinder' in result
            assert 'ellipsoid' in result
    
    def test_get_model_parameters(self):
        """get_model_parameters should return parameter info."""
        from sans_webapp.mcp_server import get_model_parameters
        
        with patch('sans_webapp.mcp_server.SANSFitter') as MockFitterClass:
            mock_fitter = MockFitter()
            mock_fitter.set_model('sphere')
            MockFitterClass.return_value = mock_fitter
            
            result = get_model_parameters('sphere')
            
            assert 'radius' in result
            assert 'sld' in result
    
    def test_set_model_when_tools_enabled(self, mock_fitter, mock_session_state):
        """set_model should work when tools are enabled."""
        from sans_webapp.mcp_server import set_model, set_fitter, set_state_accessor
        
        mock_session_state.ai_tools_enabled = True
        set_fitter(mock_fitter)
        set_state_accessor(mock_session_state)
        
        result = set_model('sphere')
        
        assert 'sphere' in result
        assert mock_session_state.current_model == 'sphere'
        assert mock_session_state.model_selected is True
    
    def test_set_model_when_tools_disabled(self, mock_fitter, mock_session_state):
        """set_model should refuse when tools are disabled."""
        from sans_webapp.mcp_server import set_model, set_fitter, set_state_accessor
        
        mock_session_state.ai_tools_enabled = False
        set_fitter(mock_fitter)
        set_state_accessor(mock_session_state)
        
        result = set_model('sphere')
        
        assert 'disabled' in result.lower()
        assert mock_session_state.model_selected is False
    
    def test_set_parameter(self, mock_fitter, mock_session_state):
        """set_parameter should update parameter values."""
        from sans_webapp.mcp_server import set_parameter, set_fitter, set_state_accessor
        
        mock_session_state.ai_tools_enabled = True
        mock_fitter.set_model('sphere')
        set_fitter(mock_fitter)
        set_state_accessor(mock_session_state)
        
        result = set_parameter('radius', value=100.0)
        
        assert 'radius' in result
        assert 'updated' in result.lower() or '100' in result
    
    def test_run_fit_requires_data(self, mock_fitter, mock_session_state):
        """run_fit should fail if no data is loaded."""
        from sans_webapp.mcp_server import run_fit, set_fitter, set_state_accessor
        
        mock_session_state.ai_tools_enabled = True
        mock_fitter.data = None
        set_fitter(mock_fitter)
        set_state_accessor(mock_session_state)
        
        result = run_fit()
        
        assert 'no data' in result.lower() or 'load data' in result.lower()


# =============================================================================
# Test Claude MCP client
# =============================================================================


class TestClaudeMCPClient:
    """Test the Claude MCP client."""
    
    def test_execute_tool_unknown_tool(self):
        """execute_tool should handle unknown tools."""
        from sans_webapp.services.claude_mcp_client import execute_tool
        
        result = execute_tool('unknown-tool', {})
        
        assert 'unknown' in result.lower()
    
    def test_execute_tool_list_models(self):
        """execute_tool should route to list-sans-models."""
        from sans_webapp.services.claude_mcp_client import execute_tool
        
        with patch('sans_webapp.mcp_server.get_all_models') as mock_get_models:
            mock_get_models.return_value = ['sphere', 'cylinder']
            
            result = execute_tool('list-sans-models', {})
            
            assert 'sphere' in result
    
    def test_client_requires_api_key(self):
        """ClaudeMCPClient should require an API key."""
        from sans_webapp.services.claude_mcp_client import ClaudeMCPClient
        
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError) as excinfo:
                ClaudeMCPClient()
            
            assert 'api key' in str(excinfo.value).lower()


# =============================================================================
# Test session state bridge
# =============================================================================


class TestSessionStateBridge:
    """Test the session state bridge."""
    
    def test_has_fitter_false_when_not_set(self):
        """has_fitter should return False when fitter not in session state."""
        from sans_webapp.services.mcp_state_bridge import SessionStateBridge
        
        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = MockSessionState()
            
            bridge = SessionStateBridge()
            
            # fitter not in mock session state
            assert bridge.has_fitter() is False
    
    def test_has_fitter_true_when_set(self):
        """has_fitter should return True when fitter is set."""
        from sans_webapp.services.mcp_state_bridge import SessionStateBridge
        
        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_state = MockSessionState()
            mock_state.fitter = MockFitter()
            mock_state._data['fitter'] = MockFitter()
            mock_st.session_state = mock_state
            
            bridge = SessionStateBridge()
            
            assert bridge.has_fitter() is True
    
    def test_are_tools_enabled(self):
        """are_tools_enabled should reflect session state."""
        from sans_webapp.services.mcp_state_bridge import SessionStateBridge
        
        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_state = MockSessionState()
            mock_state.ai_tools_enabled = True
            mock_st.session_state = mock_state
            
            bridge = SessionStateBridge()
            
            assert bridge.are_tools_enabled() is True
            
            mock_state.ai_tools_enabled = False
            assert bridge.are_tools_enabled() is False
    
    def test_set_needs_rerun(self):
        """set_needs_rerun should update session state."""
        from sans_webapp.services.mcp_state_bridge import SessionStateBridge
        
        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_state = MockSessionState()
            mock_st.session_state = mock_state
            
            bridge = SessionStateBridge()
            bridge.set_needs_rerun(True)
            
            assert mock_state.needs_rerun is True
    
    def test_set_fit_status_validates(self):
        """set_fit_status should validate status values."""
        from sans_webapp.services.mcp_state_bridge import SessionStateBridge
        
        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = MockSessionState()
            
            bridge = SessionStateBridge()
            
            # Valid status should work
            bridge.set_fit_status('running')
            
            # Invalid status should raise
            with pytest.raises(ValueError):
                bridge.set_fit_status('invalid_status')
    
    def test_chat_history_management(self):
        """Chat history methods should work correctly."""
        from sans_webapp.services.mcp_state_bridge import SessionStateBridge
        
        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_state = MockSessionState()
            mock_st.session_state = mock_state
            
            bridge = SessionStateBridge()
            
            # Start empty
            assert bridge.get_chat_history() == []
            
            # Append messages
            bridge.append_chat_message('user', 'Hello')
            bridge.append_chat_message('assistant', 'Hi there')
            
            history = bridge.get_chat_history()
            assert len(history) == 2
            assert history[0]['role'] == 'user'
            assert history[1]['role'] == 'assistant'
            
            # Clear
            bridge.clear_chat_history()
            assert bridge.get_chat_history() == []


# =============================================================================
# Test check_preconditions utility
# =============================================================================


class TestCheckPreconditions:
    """Test the check_preconditions utility function."""
    
    def test_check_preconditions_no_fitter(self):
        """Should fail when fitter not available."""
        from sans_webapp.services.mcp_state_bridge import check_preconditions
        
        with patch('sans_webapp.services.mcp_state_bridge.get_state_bridge') as mock_get_bridge:
            mock_bridge = MagicMock()
            mock_bridge.has_fitter.return_value = False
            mock_get_bridge.return_value = mock_bridge
            
            success, message = check_preconditions()
            
            assert success is False
            assert 'fitter' in message.lower()
    
    def test_check_preconditions_require_data(self):
        """Should fail when data required but not loaded."""
        from sans_webapp.services.mcp_state_bridge import check_preconditions
        
        with patch('sans_webapp.services.mcp_state_bridge.get_state_bridge') as mock_get_bridge:
            mock_bridge = MagicMock()
            mock_bridge.has_fitter.return_value = True
            mock_bridge.has_data.return_value = False
            mock_get_bridge.return_value = mock_bridge
            
            success, message = check_preconditions(require_data=True)
            
            assert success is False
            assert 'data' in message.lower()
    
    def test_check_preconditions_success(self):
        """Should succeed when all conditions met."""
        from sans_webapp.services.mcp_state_bridge import check_preconditions
        
        with patch('sans_webapp.services.mcp_state_bridge.get_state_bridge') as mock_get_bridge:
            mock_bridge = MagicMock()
            mock_bridge.has_fitter.return_value = True
            mock_bridge.has_data.return_value = True
            mock_bridge.has_model.return_value = True
            mock_get_bridge.return_value = mock_bridge
            
            success, message = check_preconditions(require_data=True, require_model=True)
            
            assert success is True
            assert message == ""


# =============================================================================
# Test check_tools_enabled utility
# =============================================================================


class TestCheckToolsEnabled:
    """Test the check_tools_enabled utility function."""
    
    def test_check_tools_enabled_when_disabled(self):
        """Should fail when tools are disabled."""
        from sans_webapp.services.mcp_state_bridge import check_tools_enabled
        
        with patch('sans_webapp.services.mcp_state_bridge.get_state_bridge') as mock_get_bridge:
            mock_bridge = MagicMock()
            mock_bridge.are_tools_enabled.return_value = False
            mock_get_bridge.return_value = mock_bridge
            
            enabled, message = check_tools_enabled()
            
            assert enabled is False
            assert 'disabled' in message.lower()
    
    def test_check_tools_enabled_when_enabled(self):
        """Should succeed when tools are enabled."""
        from sans_webapp.services.mcp_state_bridge import check_tools_enabled
        
        with patch('sans_webapp.services.mcp_state_bridge.get_state_bridge') as mock_get_bridge:
            mock_bridge = MagicMock()
            mock_bridge.are_tools_enabled.return_value = True
            mock_get_bridge.return_value = mock_bridge
            
            enabled, message = check_tools_enabled()
            
            assert enabled is True
