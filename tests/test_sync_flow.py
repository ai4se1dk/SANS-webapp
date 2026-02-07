"""
Integration tests for MCP tool -> UI state synchronization.

Tests the complete sync flow: tool execution -> bridge state update -> session_state.
Verifies SYNC-01, SYNC-02, SYNC-03, SYNC-04, SYNC-05, SYNC-06 requirements.
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
    """Mock for SANSFitter.

    Params are plain dicts with keys 'value', 'min', 'max', 'vary',
    'description' — matching the real SANSFitter API.
    """

    def __init__(self):
        self.model = None
        self.data = None
        self.params: dict[str, dict] = {}
        self.result = None

    def set_model(self, model_name: str):
        self.model = MagicMock()
        self.model.name = model_name
        self.params = {
            'radius': {'value': 50.0, 'min': 1, 'max': 500, 'vary': True, 'description': ''},
            'sld': {'value': 1e-6, 'min': 0, 'max': 1e-5, 'vary': True, 'description': ''},
            'sld_solvent': {'value': 6e-6, 'min': 0, 'max': 1e-5, 'vary': False, 'description': ''},
            'background': {'value': 0.001, 'min': 0, 'max': 1, 'vary': True, 'description': ''},
            'scale': {'value': 1.0, 'min': 0.001, 'max': 10, 'vary': True, 'description': ''},
        }

    def set_param(self, name: str, **kwargs):
        if name not in self.params:
            raise KeyError(f'Unknown parameter: {name}')
        for key in ('value', 'min', 'max', 'vary'):
            if key in kwargs:
                self.params[name][key] = kwargs[key]

    def fit(self):
        return self.result

    def set_structure_factor(self, sf_name: str):
        return self

    def remove_structure_factor(self):
        return self


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

            set_multiple_parameters(
                {
                    'radius': {'value': 45.0},
                    'scale': {'value': 2.0},
                }
            )

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

            set_multiple_parameters(
                {
                    'radius': {'min': 10.0, 'max': 100.0},
                    'scale': {'min': 0.5, 'max': 5.0},
                }
            )

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

            set_multiple_parameters(
                {
                    'radius': {'vary': True},
                    'background': {'vary': False},
                }
            )

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

            set_multiple_parameters(
                {
                    'radius': {'value': 50.0},
                    'scale': {'value': 1.5},
                    'background': {'value': 0.01},
                }
            )

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

            set_multiple_parameters(
                {
                    'radius': {'value': 60.0, 'min': 10.0, 'max': 200.0, 'vary': True},
                    'scale': {'value': 1.2},
                    'background': {'vary': False},
                }
            )

            # radius should have all updates
            assert mock_session_state._data['value_radius'] == 60.0
            assert mock_session_state._data['min_radius'] == 10.0
            assert mock_session_state._data['max_radius'] == 200.0
            assert mock_session_state._data['vary_radius'] is True

            # scale should have value update
            assert mock_session_state._data['value_scale'] == 1.2

            # background should have vary update
            assert mock_session_state._data['vary_background'] is False


# =============================================================================
# SYNC-04: run-fit tool parameter synchronization
# =============================================================================


class TestSyncRunFit:
    """Test SYNC-04: run-fit tool parameter synchronization."""

    def _setup_fitter_for_fit(self, mock_fitter, mock_session_state):
        """Common setup: fitter with model, data, and fit() returning a result."""
        mock_fitter.set_model('sphere')
        mock_fitter.data = MagicMock()
        mock_result = MagicMock(redchi=1.5)
        mock_fitter.fit = MagicMock(return_value=mock_result)
        mock_fitter.result = mock_result
        mock_session_state._data['fitter'] = mock_fitter

    def test_run_fit_sets_fit_completed(self, mock_fitter, mock_session_state):
        """run-fit should set fit_completed to True."""
        from sans_webapp.mcp_server import run_fit, set_fitter

        self._setup_fitter_for_fit(mock_fitter, mock_session_state)
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            run_fit()

            assert mock_session_state.fit_completed is True

    def test_run_fit_sets_fit_result(self, mock_fitter, mock_session_state):
        """run-fit should set fit_result in session_state."""
        from sans_webapp.mcp_server import run_fit, set_fitter

        self._setup_fitter_for_fit(mock_fitter, mock_session_state)
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            run_fit()

            assert mock_session_state.fit_result is not None
            assert mock_session_state.fit_result.redchi == 1.5

    def test_run_fit_syncs_varied_parameter_values(self, mock_fitter, mock_session_state):
        """run-fit should sync fitted values to value_{param} widget keys."""
        from sans_webapp.mcp_server import run_fit, set_fitter

        self._setup_fitter_for_fit(mock_fitter, mock_session_state)
        # Simulate optimizer updating values
        mock_fitter.params['radius']['value'] = 62.3
        mock_fitter.params['radius']['vary'] = True
        mock_fitter.params['sld']['value'] = 2.5e-6
        mock_fitter.params['sld']['vary'] = True
        mock_fitter.params['sld_solvent']['vary'] = False  # Not varied
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            run_fit()

            # Varied params should be synced
            assert mock_session_state._data['value_radius'] == 62.3
            assert mock_session_state._data['value_sld'] == 2.5e-6
            # Non-varied param should NOT be synced
            assert 'value_sld_solvent' not in mock_session_state._data

    def test_run_fit_syncs_pd_parameter_values(self, mock_fitter, mock_session_state):
        """run-fit should sync fitted PD values to pd_width_{param} widget keys."""
        from sans_webapp.mcp_server import run_fit, set_fitter

        self._setup_fitter_for_fit(mock_fitter, mock_session_state)
        # Add a PD parameter that was varied during fit
        mock_fitter.params['radius_pd'] = {
            'value': 0.15,
            'min': 0,
            'max': 1,
            'vary': True,
            'description': '',
        }
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            run_fit()

            # PD param should be synced to both value_ and pd_width_ keys
            assert mock_session_state._data['value_radius_pd'] == 0.15
            assert mock_session_state._data['pd_width_radius'] == 0.15

    def test_run_fit_sets_needs_rerun(self, mock_fitter, mock_session_state):
        """run-fit should set needs_rerun for UI refresh."""
        from sans_webapp.mcp_server import run_fit, set_fitter

        self._setup_fitter_for_fit(mock_fitter, mock_session_state)
        mock_session_state.needs_rerun = False
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            run_fit()

            assert mock_session_state.needs_rerun is True


# =============================================================================
# SYNC-05: enable-polydispersity tool state synchronization
# =============================================================================


class TestSyncPolydispersity:
    """Test SYNC-05: enable-polydispersity tool state synchronization."""

    def _setup_fitter_with_pd(self, mock_fitter, mock_session_state):
        """Common setup: fitter with model that has PD parameters."""
        mock_fitter.set_model('sphere')
        mock_fitter.params['radius_pd'] = {
            'value': 0.1,
            'min': 0,
            'max': 1,
            'vary': False,
            'description': '',
        }
        mock_session_state._data['fitter'] = mock_fitter

    def test_enable_polydispersity_sets_pd_enabled(self, mock_fitter, mock_session_state):
        """enable-polydispersity should set pd_enabled to True."""
        from sans_webapp.mcp_server import enable_polydispersity, set_fitter

        self._setup_fitter_with_pd(mock_fitter, mock_session_state)
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            enable_polydispersity('radius')

            assert mock_session_state.pd_enabled is True

    def test_enable_polydispersity_sets_pd_width(self, mock_fitter, mock_session_state):
        """enable-polydispersity should set pd_width_{param} in session_state."""
        from sans_webapp.mcp_server import enable_polydispersity, set_fitter

        self._setup_fitter_with_pd(mock_fitter, mock_session_state)
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            enable_polydispersity('radius', pd_value=0.15)

            assert mock_session_state._data['pd_width_radius'] == 0.15

    def test_enable_polydispersity_sets_pd_type(self, mock_fitter, mock_session_state):
        """enable-polydispersity should set pd_type_{param} in session_state."""
        from sans_webapp.mcp_server import enable_polydispersity, set_fitter

        self._setup_fitter_with_pd(mock_fitter, mock_session_state)
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            enable_polydispersity('radius', pd_type='lognormal')

            assert mock_session_state._data['pd_type_radius'] == 'lognormal'

    def test_enable_polydispersity_sets_pd_vary(self, mock_fitter, mock_session_state):
        """enable-polydispersity should set pd_vary_{param} to True."""
        from sans_webapp.mcp_server import enable_polydispersity, set_fitter

        self._setup_fitter_with_pd(mock_fitter, mock_session_state)
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            enable_polydispersity('radius')

            assert mock_session_state._data['pd_vary_radius'] is True

    def test_enable_polydispersity_sets_needs_rerun(self, mock_fitter, mock_session_state):
        """enable-polydispersity should set needs_rerun for UI refresh."""
        from sans_webapp.mcp_server import enable_polydispersity, set_fitter

        self._setup_fitter_with_pd(mock_fitter, mock_session_state)
        mock_session_state.needs_rerun = False
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            enable_polydispersity('radius')

            assert mock_session_state.needs_rerun is True


# =============================================================================
# SYNC-06: structure factor tools widget clearing
# =============================================================================


class TestSyncStructureFactor:
    """Test SYNC-06: structure factor tools widget clearing."""

    def test_set_structure_factor_clears_parameter_widgets(self, mock_fitter, mock_session_state):
        """set-structure-factor should clear old parameter widget keys."""
        from sans_webapp.mcp_server import set_fitter, set_structure_factor

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        # Pre-existing parameter widgets
        mock_session_state._data['value_radius'] = 50.0
        mock_session_state._data['min_radius'] = 1.0
        mock_session_state._data['max_radius'] = 500.0
        mock_session_state._data['vary_radius'] = True
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_structure_factor('hardsphere')

            # Old parameter widget keys should be cleared
            assert 'value_radius' not in mock_session_state._data
            assert 'min_radius' not in mock_session_state._data
            assert 'max_radius' not in mock_session_state._data
            assert 'vary_radius' not in mock_session_state._data

    def test_set_structure_factor_sets_needs_rerun(self, mock_fitter, mock_session_state):
        """set-structure-factor should set needs_rerun for UI refresh."""
        from sans_webapp.mcp_server import set_fitter, set_structure_factor

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        mock_session_state.needs_rerun = False
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            set_structure_factor('hardsphere')

            assert mock_session_state.needs_rerun is True

    def test_remove_structure_factor_clears_parameter_widgets(
        self, mock_fitter, mock_session_state
    ):
        """remove-structure-factor should clear parameter widget keys."""
        from sans_webapp.mcp_server import remove_structure_factor, set_fitter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        # Pre-existing widgets (including SF params)
        mock_session_state._data['value_radius'] = 50.0
        mock_session_state._data['vary_radius'] = True
        mock_session_state._data['value_volfraction'] = 0.2
        mock_session_state._data['vary_volfraction'] = True
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            remove_structure_factor()

            # All parameter widget keys should be cleared
            assert 'value_radius' not in mock_session_state._data
            assert 'vary_radius' not in mock_session_state._data
            assert 'value_volfraction' not in mock_session_state._data
            assert 'vary_volfraction' not in mock_session_state._data

    def test_remove_structure_factor_sets_needs_rerun(self, mock_fitter, mock_session_state):
        """remove-structure-factor should set needs_rerun for UI refresh."""
        from sans_webapp.mcp_server import remove_structure_factor, set_fitter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        mock_session_state.needs_rerun = False
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            remove_structure_factor()

            assert mock_session_state.needs_rerun is True
