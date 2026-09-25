"""
Tests for Save & Load: sans-fitter analysis files and reports, and replacing
the app's fitter with a loaded one.
"""

from unittest.mock import patch

import pytest
from sans_fitter import SANSFitter, examples

from sans_webapp import sans_analysis_utils as utils
from sans_webapp.services import session_state

EXAMPLE_DATA = 'simulated_sans_data.csv'


@pytest.fixture(scope='module')
def fitted():
    """A sphere fit with a restricted Q range and a pinhole resolution."""
    fitter = SANSFitter()
    fitter.load_data(EXAMPLE_DATA)
    fitter.set_model('sphere')
    fitter.set_param('radius', value=40.0, min=5.0, max=200.0, vary=True)
    fitter.set_q_range(qmin=0.005)
    fitter.set_resolution('pinhole', dq_over_q=0.05)
    fitter.fit(engine='bumps', method='amoeba')
    return fitter


class TestAnalysisFiles:
    def test_round_trip_onto_the_same_data_restores_setup_and_fit(self, fitted):
        contents = utils.analysis_json(fitted).encode()
        restored = utils.load_analysis_onto_data(contents, fitted.data)

        assert restored is not fitted
        assert restored.model_name == 'sphere'
        assert restored.params['radius'] == fitted.params['radius']
        assert restored.get_q_range() == fitted.get_q_range()
        assert restored.get_resolution() == fitted.get_resolution()
        assert restored.fit_result is not None
        assert restored.fit_result['reduced_chisq'] == pytest.approx(
            fitted.fit_result['reduced_chisq']
        )

    def test_onto_other_data_restores_setup_without_the_fit(self, fitted):
        contents = utils.analysis_json(fitted).encode()
        restored = utils.load_analysis_onto_data(contents, examples.load('sphere'))

        assert restored.params['radius']['value'] == fitted.params['radius']['value']
        assert restored.get_resolution() == fitted.get_resolution()
        assert restored.fit_result is None

    def test_invalid_file_is_rejected(self, fitted):
        with pytest.raises(ValueError):
            utils.load_analysis_onto_data(b'{"not": "an analysis"}', fitted.data)

    def test_report_is_html_naming_the_model(self, fitted):
        html = utils.report_html(fitted)
        assert html.lstrip().lower().startswith('<!doctype html')
        assert 'sphere' in html


class AttrDict(dict):
    """Stand-in for st.session_state: a dict that also takes attribute access."""

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class TestAdoptFitter:
    def test_replaces_fitter_and_resets_widget_state(self, fitted):
        state = AttrDict(
            fitter=SANSFitter(),
            value_radius=1.0,
            vary_radius=False,
            pd_enabled=True,
            param_updates={},
            fit_qmin=0.1,
            fit_warnings=['old warning'],
            unrelated='kept',
        )
        with patch.object(session_state.st, 'session_state', state):
            session_state.adopt_fitter(fitted)

        assert state.fitter is fitted
        for key in ('value_radius', 'vary_radius', 'pd_enabled', 'param_updates', 'fit_qmin'):
            assert key not in state
        assert state.unrelated == 'kept'
        assert state.data_loaded is True
        assert state.model_selected is True
        assert state.current_model == 'sphere'
        assert state.fit_completed is True
        assert state.fit_result is fitted.fit_result
        assert state.fit_warnings == []

    def test_fitter_without_fit_clears_the_old_result(self):
        fitter = SANSFitter()
        fitter.load_data(EXAMPLE_DATA)
        fitter.set_model('sphere')
        state = AttrDict(fitter=SANSFitter(), fit_completed=True, fit_result={'chisq': 1.0})
        with patch.object(session_state.st, 'session_state', state):
            session_state.adopt_fitter(fitter)

        assert state.fit_completed is False
        assert 'fit_result' not in state


def _sidebar_app():
    import streamlit as st
    from sans_fitter import SANSFitter

    from sans_webapp.components.analysis_files import render_analysis_files_sidebar

    if 'fitter' not in st.session_state:
        fitter = SANSFitter()
        if st.session_state.with_model:
            fitter.load_data('simulated_sans_data.csv')
            fitter.set_model('sphere')
        st.session_state.fitter = fitter
        st.session_state.model_selected = st.session_state.with_model
        st.session_state.data_loaded = st.session_state.with_model
    render_analysis_files_sidebar()


@pytest.mark.parametrize('with_model', [True, False])
def test_sidebar_offers_downloads_only_with_a_model(with_model):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_sidebar_app, default_timeout=30)
    at.session_state['with_model'] = with_model
    at.run()
    assert not at.exception
    assert len(at.get('download_button')) == (2 if with_model else 0)


# -----------------------------------------------------------------------------
# Results slider starts at the fitted value (ordinary fit, loaded analysis)
# -----------------------------------------------------------------------------


def _assert_slider_shows(at, fitter):
    slider = at.slider[0]
    param = at.session_state['selected_slider_param']
    assert slider.value == pytest.approx(fitter.params[param]['value'])
    assert slider.min <= slider.value <= slider.max


def test_slider_starts_at_the_fitted_value_after_a_fit():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    app_file = Path(__file__).parent.parent / 'src' / 'sans_webapp' / 'app.py'
    at = AppTest.from_file(str(app_file), default_timeout=90).run()
    for label in ('Load Example Data', 'Load Model', 'Fit All Parameters', '🚀 Run Fit'):
        next(b for b in at.button if b.label == label).click().run()

    assert not at.exception
    _assert_slider_shows(at, at.session_state.fitter)


def _adopt_over_fit_app():
    import streamlit as st
    from sans_fitter import SANSFitter

    from sans_webapp.components.fit_results import render_fit_results
    from sans_webapp.services.session_state import adopt_fitter, init_session_state

    def fitted(radius, min_radius):
        fitter = SANSFitter()
        fitter.load_data('simulated_sans_data.csv')
        fitter.set_model('sphere')
        fitter.set_param('radius', value=radius, min=min_radius, max=500.0, vary=True)
        fitter.fit(engine='bumps', method='amoeba')
        return fitter

    init_session_state()
    if st.session_state.get('step') == 'fit':
        adopt_fitter(fitted(40.0, min_radius=1.0))
        st.session_state.step = 'shown'
    elif st.session_state.get('step') == 'load':
        # Stands in for a loaded analysis; its bounds keep the radius far from the first
        adopt_fitter(fitted(120.0, min_radius=100.0))
        st.session_state.step = 'loaded'
    render_fit_results(st.session_state.fitter, {})


def test_slider_follows_a_fitter_adopted_over_an_existing_fit():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_adopt_over_fit_app, default_timeout=90)
    at.session_state['step'] = 'fit'
    at.run()
    first_value = at.slider[0].value
    _assert_slider_shows(at, at.session_state.fitter)

    at.session_state['step'] = 'load'
    at.run()
    assert not at.exception
    _assert_slider_shows(at, at.session_state.fitter)
    assert at.slider[0].value != pytest.approx(first_value)
