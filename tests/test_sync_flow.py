"""
Integration tests for MCP tool -> UI state synchronization.

Tests the complete sync flow: tool execution -> bridge state update -> session_state.
Verifies SYNC-01, SYNC-02, SYNC-03 requirements.
"""

from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Test fixtures
# =============================================================================


class MockSessionState:
    """Mock for Streamlit session_state with full dict-like behavior."""

    def __init__(self):
        self._data = {
            'ai_tools_enabled': True,
            'needs_rerun': False,
            'current_model': None,
            'model_selected': False,
            'fit_completed': False,
            'fit_status': 'idle',
            'chat_history': [],
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

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

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
            'scale': MagicMock(value=1.0, bounds=(0.001, 10), vary=True),
        }


@pytest.fixture
def mock_session_state():
    """Create a mock session state."""
    return MockSessionState()


@pytest.fixture
def mock_fitter():
    """Create a mock fitter."""
    return MockFitter()


# =============================================================================
# SYNC-01: set-model tool state synchronization
# =============================================================================


class TestSyncSetModel:
    """Test SYNC-01: set-model tool state synchronization."""

    def test_set_model_updates_current_model(self, mock_fitter, mock_session_state):
        """set-model should update st.session_state.current_model."""
        from sans_webapp.mcp_server import set_fitter, set_model

        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            result = set_model('cylinder')

            assert 'cylinder' in result
            assert mock_session_state.current_model == 'cylinder'

    def test_set_model_sets_model_selected_flag(self, mock_fitter, mock_session_state):
        """set-model should set model_selected to True."""
        from sans_webapp.mcp_server import set_fitter, set_model

        mock_session_state._data['fitter'] = mock_fitter
        mock_session_state.model_selected = False
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_model('sphere')

            assert mock_session_state.model_selected is True

    def test_set_model_clears_fit_completed(self, mock_fitter, mock_session_state):
        """set-model should reset fit_completed to False."""
        from sans_webapp.mcp_server import set_fitter, set_model

        mock_session_state._data['fitter'] = mock_fitter
        mock_session_state.fit_completed = True  # Was True from previous fit
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_model('ellipsoid')

            assert mock_session_state.fit_completed is False

    def test_set_model_sets_needs_rerun(self, mock_fitter, mock_session_state):
        """set-model should set needs_rerun to True for UI refresh."""
        from sans_webapp.mcp_server import set_fitter, set_model

        mock_session_state._data['fitter'] = mock_fitter
        mock_session_state.needs_rerun = False
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_model('sphere')

            assert mock_session_state.needs_rerun is True

    def test_set_model_clears_old_parameter_widgets(self, mock_fitter, mock_session_state):
        """set-model should clear old parameter widget keys."""
        from sans_webapp.mcp_server import set_fitter, set_model

        # Set up old parameter widget state
        mock_session_state._data['value_old_param'] = 100.0
        mock_session_state._data['min_old_param'] = 0.0
        mock_session_state._data['max_old_param'] = 200.0
        mock_session_state._data['vary_old_param'] = True
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_model('sphere')

            # Old parameter widget keys should be cleared
            assert 'value_old_param' not in mock_session_state._data
            assert 'min_old_param' not in mock_session_state._data
            assert 'max_old_param' not in mock_session_state._data
            assert 'vary_old_param' not in mock_session_state._data


# =============================================================================
# SYNC-02: set-parameter tool widget synchronization
# =============================================================================


class TestSyncSetParameter:
    """Test SYNC-02: set-parameter tool widget synchronization."""

    def test_set_parameter_updates_value_widget(self, mock_fitter, mock_session_state):
        """set-parameter should update value_{name} in session_state."""
        from sans_webapp.mcp_server import set_fitter, set_parameter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_parameter('radius', value=75.0)

            assert mock_session_state._data['value_radius'] == 75.0

    def test_set_parameter_updates_min_widget(self, mock_fitter, mock_session_state):
        """set-parameter should update min_{name} when min_bound provided."""
        from sans_webapp.mcp_server import set_fitter, set_parameter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_parameter('radius', min_bound=10.0)

            assert mock_session_state._data['min_radius'] == 10.0

    def test_set_parameter_updates_max_widget(self, mock_fitter, mock_session_state):
        """set-parameter should update max_{name} when max_bound provided."""
        from sans_webapp.mcp_server import set_fitter, set_parameter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_parameter('radius', max_bound=200.0)

            assert mock_session_state._data['max_radius'] == 200.0

    def test_set_parameter_updates_vary_widget(self, mock_fitter, mock_session_state):
        """set-parameter should update vary_{name} when vary provided."""
        from sans_webapp.mcp_server import set_fitter, set_parameter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_parameter('radius', vary=False)

            assert mock_session_state._data['vary_radius'] is False

    def test_set_parameter_sets_needs_rerun(self, mock_fitter, mock_session_state):
        """set-parameter should set needs_rerun for UI refresh."""
        from sans_webapp.mcp_server import set_fitter, set_parameter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        mock_session_state.needs_rerun = False
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_parameter('radius', value=60.0)

            assert mock_session_state.needs_rerun is True

    def test_set_parameter_updates_all_widgets_at_once(self, mock_fitter, mock_session_state):
        """set-parameter should update all provided widget values."""
        from sans_webapp.mcp_server import set_fitter, set_parameter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_parameter('radius', value=80.0, min_bound=5.0, max_bound=300.0, vary=True)

            assert mock_session_state._data['value_radius'] == 80.0
            assert mock_session_state._data['min_radius'] == 5.0
            assert mock_session_state._data['max_radius'] == 300.0
            assert mock_session_state._data['vary_radius'] is True


# =============================================================================
# SYNC-03: set-multiple-parameters atomic updates
# =============================================================================


class TestSyncSetMultipleParameters:
    """Test SYNC-03: set-multiple-parameters atomic updates."""

    def test_set_multiple_parameters_updates_all_values(self, mock_fitter, mock_session_state):
        """set-multiple-parameters should update all specified values."""
        from sans_webapp.mcp_server import set_fitter, set_multiple_parameters

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_multiple_parameters({
                'radius': {'value': 45.0},
                'scale': {'value': 2.0},
            })

            assert mock_session_state._data['value_radius'] == 45.0
            assert mock_session_state._data['value_scale'] == 2.0

    def test_set_multiple_parameters_updates_bounds(self, mock_fitter, mock_session_state):
        """set-multiple-parameters should update bounds for all specified."""
        from sans_webapp.mcp_server import set_fitter, set_multiple_parameters

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_multiple_parameters({
                'radius': {'min': 10.0, 'max': 100.0},
                'scale': {'min': 0.5, 'max': 5.0},
            })

            assert mock_session_state._data['min_radius'] == 10.0
            assert mock_session_state._data['max_radius'] == 100.0
            assert mock_session_state._data['min_scale'] == 0.5
            assert mock_session_state._data['max_scale'] == 5.0

    def test_set_multiple_parameters_updates_vary_flags(self, mock_fitter, mock_session_state):
        """set-multiple-parameters should update vary flags for all specified."""
        from sans_webapp.mcp_server import set_fitter, set_multiple_parameters

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_multiple_parameters({
                'radius': {'vary': True},
                'background': {'vary': False},
            })

            assert mock_session_state._data['vary_radius'] is True
            assert mock_session_state._data['vary_background'] is False

    def test_set_multiple_parameters_single_rerun(self, mock_fitter, mock_session_state):
        """set-multiple-parameters should set needs_rerun once at end."""
        from sans_webapp.mcp_server import set_fitter, set_multiple_parameters

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        mock_session_state.needs_rerun = False
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_multiple_parameters({
                'radius': {'value': 50.0},
                'scale': {'value': 1.5},
                'background': {'value': 0.01},
            })

            # needs_rerun should be True (set once at end)
            assert mock_session_state.needs_rerun is True

    def test_set_multiple_parameters_mixed_updates(self, mock_fitter, mock_session_state):
        """set-multiple-parameters should handle mixed value/bounds/vary updates."""
        from sans_webapp.mcp_server import set_fitter, set_multiple_parameters

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_multiple_parameters({
                'radius': {'value': 60.0, 'min': 10.0, 'max': 200.0, 'vary': True},
                'scale': {'value': 1.2},
                'background': {'vary': False},
            })

            # radius should have all updates
            assert mock_session_state._data['value_radius'] == 60.0
            assert mock_session_state._data['min_radius'] == 10.0
            assert mock_session_state._data['max_radius'] == 200.0
            assert mock_session_state._data['vary_radius'] is True

            # scale should have value update
            assert mock_session_state._data['value_scale'] == 1.2

            # background should have vary update
            assert mock_session_state._data['vary_background'] is False
