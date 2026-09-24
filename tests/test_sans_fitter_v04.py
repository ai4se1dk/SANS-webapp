"""
Tests for the sans-fitter >= 0.4 integration.

Covers the Streamlit-free helpers in ``sans_analysis_utils`` against a real
``SANSFitter`` (result shape, warnings capture, model evaluation on the data
grid, state description) and the MCP tools that were adapted to the new API
(``set-q-range``, ``run-fit``, ``enable-polydispersity``, ``get-fit-results``).
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from conftest import MockFitter, MockSessionState
from sans_fitter import SANSFitter

from sans_webapp import sans_analysis_utils as utils

EXAMPLE_DATA = 'simulated_sans_data.csv'


@pytest.fixture(scope='module')
def fitted_sphere():
    """A real fitter with the example data fitted by a sphere model (bumps/amoeba)."""
    fitter = SANSFitter()
    fitter.load_data(EXAMPLE_DATA)
    fitter.set_model('sphere')
    fitter.set_param('scale', value=1.0, min=0.01, max=10.0, vary=True)
    fitter.set_param('background', value=0.001, min=0.0, max=1.0, vary=True)
    fitter.set_param('radius', value=40.0, min=5.0, max=200.0, vary=True)
    result, fit_warnings = utils.run_fit_with_warnings(fitter, engine='bumps', method='amoeba')
    return fitter, result, fit_warnings


# =============================================================================
# Real-fitter helpers
# =============================================================================


class TestRealFitterHelpers:
    def test_fit_result_has_04_shape(self, fitted_sphere):
        _fitter, result, fit_warnings = fitted_sphere
        for key in ('engine', 'method', 'chisq', 'reduced_chisq', 'n_points', 'n_free', 'dof'):
            assert key in result, f'missing {key}'
        assert result['engine'] == 'bumps'
        assert result['n_free'] == 3
        assert result['dof'] == result['n_points'] - result['n_free']
        # Raw chi-squared vs reduced chi-squared are related by dof
        assert result['chisq'] == pytest.approx(result['reduced_chisq'] * result['dof'])
        assert isinstance(fit_warnings, list)
        assert all(isinstance(message, str) for message in fit_warnings)

    def test_parameters_block_flags_fixed(self, fitted_sphere):
        _fitter, result, _ = fitted_sphere
        parameters = result['parameters']
        # Every model parameter is reported, fixed ones flagged
        assert set(parameters) >= {'scale', 'background', 'radius', 'sld', 'sld_solvent'}
        assert parameters['radius']['fixed'] is False
        assert parameters['sld']['fixed'] is True
        assert 'formatted' in parameters['radius']

    def test_evaluate_model_matches_data_grid(self, fitted_sphere):
        fitter, _, _ = fitted_sphere
        curve = utils.evaluate_model(fitter)
        assert curve.shape == fitter.data.x.shape
        assert np.all(np.isfinite(curve))

    def test_evaluate_model_respects_q_range(self):
        fitter = SANSFitter()
        fitter.load_data(EXAMPLE_DATA)
        fitter.set_model('sphere')
        qmin = float(np.sort(fitter.data.x)[10])
        fitter.set_q_range(qmin=qmin)
        try:
            curve = utils.evaluate_model(fitter)
            outside = fitter.data.x < qmin
            assert np.all(np.isnan(curve[outside]))
            assert np.all(np.isfinite(curve[~outside]))
            residuals = utils.calculate_residuals(fitter.data.y, curve, fitter.data.dy)
            assert np.all(np.isnan(residuals[outside]))
        finally:
            fitter.reset_q_range()
        assert fitter.get_q_range() == (fitter.data.x.min(), fitter.data.x.max())

    def test_fit_is_current_tracks_changes_after_fit(self):
        fitter = SANSFitter()
        fitter.load_data(EXAMPLE_DATA)
        fitter.set_model('sphere')
        fitter.set_param('radius', value=40.0, min=5.0, max=200.0, vary=True)
        assert utils.fit_is_current(fitter) is False  # no fit yet

        fitter.fit(engine='bumps', method='amoeba')
        assert utils.fit_is_current(fitter) is True

        fitted_radius = fitter.params['radius']['value']
        fitter.set_param('radius', value=fitted_radius * 1.1)
        assert utils.fit_is_current(fitter) is False
        fitter.set_param('radius', value=fitted_radius)
        assert utils.fit_is_current(fitter) is True

        fitter.set_q_range(qmin=float(np.sort(fitter.data.x)[10]))
        assert utils.fit_is_current(fitter) is False

    def test_fit_is_current_falls_back_when_private_check_fails(self):
        fitter = SANSFitter()
        fitter.load_data(EXAMPLE_DATA)
        fitter.set_model('sphere')
        fitter.set_param('radius', value=40.0, min=5.0, max=200.0, vary=True)
        fitter.fit(engine='bumps', method='amoeba')
        with patch('sans_fitter.persistence.compare_fit_context', side_effect=TypeError('changed')):
            assert utils.fit_is_current(fitter) is False
            # The figure still renders, as the model preview
            fig = utils.plot_fit_results(fitter)
        assert fig.layout.title.text.startswith('Model preview')

    def test_quiet_fitter_leaves_logger_level_and_other_threads_alone(self):
        import logging
        import threading

        logger = logging.getLogger('sans_fitter')
        level = logger.level
        seen = []

        class Collect(logging.Handler):
            def emit(self, record):
                seen.append(record.getMessage())

        handler = Collect()
        logger.addHandler(handler)
        try:
            with utils._quiet_fitter():
                logger.info('own thread')
                logger.error('own thread error')
                other = threading.Thread(target=lambda: logger.info('other thread'))
                other.start()
                other.join()
            logger.info('after')
        finally:
            logger.removeHandler(handler)

        assert logger.level == level
        assert logger.filters == []
        assert seen == ['own thread error', 'other thread', 'after']

    def test_plot_fit_results_switches_between_fit_and_preview(self):
        fitter = SANSFitter()
        fitter.load_data(EXAMPLE_DATA)
        fitter.set_model('sphere')
        fitter.set_param('radius', value=40.0, min=5.0, max=200.0, vary=True)
        fitter.fit(engine='bumps', method='amoeba')

        fig = utils.plot_fit_results(fitter)
        assert fig.layout.title.text.startswith('SANS Fit')
        assert 'Fitted Model' in [trace.name for trace in fig.data]

        # A parameter moved after the fit: show the model at the new value
        fitter.set_param('radius', value=fitter.params['radius']['value'] * 1.1)
        fig = utils.plot_fit_results(fitter)
        assert fig.layout.title.text.startswith('Model preview')

    def test_plot_fit_results_marks_points_outside_q_range(self):
        fitter = SANSFitter()
        fitter.load_data(EXAMPLE_DATA)
        fitter.set_model('sphere')
        fitter.set_q_range(qmin=float(np.sort(fitter.data.x)[10]))
        fig = utils.plot_fit_results(fitter)
        excluded = [trace for trace in fig.data if trace.name == 'Excluded Data']
        assert len(excluded) == 1
        assert len(excluded[0].x) == 10

    def test_data_column_summary(self, fitted_sphere):
        fitter, _, _ = fitted_sphere
        summary = utils.data_column_summary(fitter.data)
        assert summary == {'has_dy': True, 'has_dx': False}

    def test_data_column_summary_tolerates_mocks(self):
        assert utils.data_column_summary(MagicMock()) == {'has_dy': False, 'has_dx': False}
        assert utils.data_column_summary(None) == {'has_dy': False, 'has_dx': False}

    def test_describe_fitter_state_real(self, fitted_sphere):
        fitter, _, _ = fitted_sphere
        text = '\n'.join(utils.describe_fitter_state(fitter))
        assert 'Data:' in text
        assert 'Fit Q range' in text
        assert 'Resolution mode: data' in text
        assert 'Model: sphere' in text
        assert 'radius' in text
        assert 'Polydispersity: disabled' in text
        assert 'Last fit:' in text
        assert 'Reduced chi-squared' in text

    def test_describe_fitter_state_tolerates_mocks(self):
        # A bare MagicMock returns MagicMocks for everything; must not raise.
        lines = utils.describe_fitter_state(MagicMock())
        assert isinstance(lines, list)
        # An empty fitter reports nothing loaded
        lines = utils.describe_fitter_state(SANSFitter())
        assert 'Data: Not loaded' in lines
        assert 'Model: Not selected' in lines

    def test_fit_report_markdown(self, fitted_sphere):
        fitter, _, _ = fitted_sphere
        markdown = fitter.get_fit_report().to_markdown()
        assert 'radius' in markdown

    def test_run_fit_with_warnings_captures_bound_warning(self):
        fitter = SANSFitter()
        fitter.load_data(EXAMPLE_DATA)
        fitter.set_model('sphere')
        # Trap the background at its lower bound so sans-fitter warns about it
        fitter.set_param('background', value=0.0, min=0.0, max=1e-12, vary=True)
        fitter.set_param('scale', value=1.0, min=0.01, max=10.0, vary=True)
        result, fit_warnings = utils.run_fit_with_warnings(fitter, engine='lmfit')
        assert 'reduced_chisq' in result
        if result['on_bounds']:
            assert any('bound' in message for message in fit_warnings)


# =============================================================================
# Formatting helpers (dict inputs)
# =============================================================================


class TestFormatting:
    def test_format_fit_summary_full(self):
        lines = utils.format_fit_summary(
            {
                'engine': 'bumps',
                'method': 'amoeba',
                'chisq': 30.0,
                'reduced_chisq': 1.5,
                'n_points': 23,
                'n_free': 3,
                'dof': 20,
                'converged': False,
                'message': 'max iterations',
                'on_bounds': [('radius', 'max')],
            }
        )
        text = '\n'.join(lines)
        assert 'Engine: bumps / amoeba' in text
        assert 'Reduced chi-squared (chi2/dof): 1.5000' in text
        assert 'Chi-squared (raw): 30.0000' in text
        assert 'Points fitted: 23' in text
        assert 'Converged: NO (max iterations)' in text
        assert 'Parameters at a bound: radius (max)' in text

    def test_format_fit_summary_legacy_and_nan(self):
        assert utils.format_fit_summary({'chisq': 2.0}) == ['Chi-squared: 2.0000']
        lines = utils.format_fit_summary({'chisq': float('nan'), 'reduced_chisq': float('nan')})
        assert 'n/a' in lines[0]

    def test_format_fit_parameters(self):
        result = {
            'parameters': {
                'radius': {'value': 62.3, 'stderr': 1.5, 'formatted': '62.3 ± 1.5', 'fixed': False},
                'sld': {'value': 1.0, 'stderr': 0.0, 'formatted': '1 (fixed)', 'fixed': True},
                'legacy': {'value': 3.0, 'stderr': 0.1},
            }
        }
        varied = utils.format_fit_parameters(result)
        assert varied == ['  - radius: 62.3 ± 1.5', '  - legacy: 3 ± 0.1']
        everything = utils.format_fit_parameters(result, include_fixed=True)
        assert '  - sld: 1 (fixed)' in everything


# =============================================================================
# MCP tools against the mock fitter
# =============================================================================


class TestSetQRangeTool:
    def _setup(self, mock_fitter, mock_session_state):
        mock_fitter.load_data('test_data.csv')
        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter

    def test_set_q_range_updates_fitter_and_widgets(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import set_fitter, set_q_range

        self._setup(mock_fitter, mock_session_state)
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            result = set_q_range(qmin=0.02, qmax=0.04)

            assert 'updated' in result
            assert '3 of 5 points' in result
            assert mock_fitter.get_q_range() == (0.02, 0.04)
            assert mock_session_state._data['fit_qmin'] == 0.02
            assert mock_session_state._data['fit_qmax'] == 0.04
            assert mock_session_state.needs_rerun is True

    def test_set_q_range_without_arguments_resets(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import set_fitter, set_q_range

        self._setup(mock_fitter, mock_session_state)
        mock_fitter.set_q_range(qmin=0.02)
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            result = set_q_range()

            assert 'reset' in result
            assert mock_fitter.get_q_range() == (0.01, 0.05)
            assert mock_session_state._data['fit_qmin'] == 0.01

    def test_set_q_range_reports_invalid_range(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import set_fitter, set_q_range

        self._setup(mock_fitter, mock_session_state)
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            result = set_q_range(qmin=0.05, qmax=0.01)

            assert result.startswith('Error')
            assert mock_fitter.get_q_range() == (0.01, 0.05)

    def test_set_q_range_requires_data(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import set_fitter, set_q_range

        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            assert 'No data loaded' in set_q_range(qmin=0.02)

    def test_set_q_range_refuses_when_tools_disabled(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import set_fitter, set_q_range

        self._setup(mock_fitter, mock_session_state)
        mock_session_state.ai_tools_enabled = False
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            assert 'disabled' in set_q_range(qmin=0.02).lower()
            assert mock_fitter.get_q_range() == (0.01, 0.05)


class TestRunFitTool:
    def test_run_fit_reports_reduced_chisq_and_parameters(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import run_fit, set_fitter

        mock_fitter.load_data('test_data.csv')
        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            result = run_fit()

            assert result.startswith('Fit completed!')
            assert 'Reduced chi-squared (chi2/dof): 1.5000' in result
            assert 'radius' in result
            # Fixed parameters are not listed as optimized
            assert 'sld_solvent' not in result
            assert mock_session_state.fit_warnings == []

    def test_run_fit_syncs_param_updates_store(self, mock_fitter, mock_session_state):
        """A fitted value must reach param_updates or the next UI fit reverts it."""
        from sans_webapp.mcp_server import run_fit, set_fitter

        mock_fitter.load_data('test_data.csv')
        mock_fitter.set_model('sphere')
        mock_fitter.params['radius']['value'] = 62.3
        mock_session_state._data['fitter'] = mock_fitter
        mock_session_state._data['param_updates'] = {
            'radius': {'value': 50.0, 'min': 1, 'max': 500, 'vary': True}
        }
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            run_fit()

            assert mock_session_state._data['param_updates']['radius']['value'] == 62.3

    def test_run_fit_passes_engine_and_method(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import run_fit, set_fitter

        mock_fitter.load_data('test_data.csv')
        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            result = run_fit(engine='lmfit', method='least_squares')

            assert 'Engine: lmfit / least_squares' in result
            assert mock_session_state.fit_result['engine'] == 'lmfit'


class TestGetFitResultsTool:
    def test_no_fit_yet(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import get_fit_results, set_fitter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        assert 'No fit results' in get_fit_results()

    def test_after_fit(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import get_fit_results, set_fitter

        mock_fitter.load_data('test_data.csv')
        mock_fitter.set_model('sphere')
        mock_fitter.fit()
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        result = get_fit_results()

        assert 'Reduced chi-squared (chi2/dof): 1.5000' in result
        assert 'Optimized parameters:' in result
        assert 'Fixed / linked parameters:' in result
        assert 'sld_solvent' in result


class TestEnablePolydispersityTool:
    def test_configures_fitter_pd_api(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import enable_polydispersity, set_fitter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            result = enable_polydispersity('radius', pd_type='schulz', pd_value=0.2)

            assert 'enabled' in result
            assert mock_fitter.is_polydispersity_enabled()
            config = mock_fitter.get_pd_param('radius')
            assert config['pd'] == 0.2
            assert config['pd_type'] == 'schulz'
            assert config['vary'] is True
            assert mock_session_state._data['pd_n_radius'] == 35

    def test_unknown_parameter_lists_available(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import enable_polydispersity, set_fitter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            result = enable_polydispersity('sld')

            assert 'not a polydisperse parameter' in result
            assert 'radius' in result
            assert not mock_fitter.is_polydispersity_enabled()

    def test_invalid_distribution_reports_error(self, mock_fitter, mock_session_state):
        from sans_webapp.mcp_server import enable_polydispersity, set_fitter

        mock_fitter.set_model('sphere')
        mock_session_state._data['fitter'] = mock_fitter
        set_fitter(mock_fitter)

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            mock_st.session_state = mock_session_state

            assert 'Error' in enable_polydispersity('radius', pd_type='triangular')


class TestStateBridgeSync:
    def test_pd_widget_updates_pd_updates_store(self):
        from sans_webapp.services.mcp_state_bridge import SessionStateBridge

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            state = MockSessionState()
            state._data['pd_updates'] = {
                'radius': {'pd_width': 0.0, 'pd_n': 35, 'pd_type': 'gaussian', 'vary': False}
            }
            mock_st.session_state = state

            SessionStateBridge().set_pd_widget('radius', pd_width=0.15, vary=True)

            assert state._data['pd_width_radius'] == 0.15
            assert state._data['pd_updates']['radius']['pd_width'] == 0.15
            assert state._data['pd_updates']['radius']['vary'] is True
            assert state._data['pd_updates']['radius']['pd_type'] == 'gaussian'

    def test_q_range_widgets(self):
        from sans_webapp.services.mcp_state_bridge import SessionStateBridge

        with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
            state = MockSessionState()
            mock_st.session_state = state
            bridge = SessionStateBridge()

            bridge.set_q_range_widgets(0.01, 0.2)
            assert state._data['fit_qmin'] == 0.01
            assert state._data['fit_qmax'] == 0.2

            bridge.clear_q_range_widgets()
            assert 'fit_qmin' not in state._data
