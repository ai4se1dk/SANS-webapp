"""
Tests for Save & Load: sans-fitter analysis files and reports, and replacing
the app's fitter with a loaded one.
"""

import json
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
    # The default example (sphere) loads with its model
    for label in ('Load Example', 'Fit All Parameters', '🚀 Run Fit'):
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


# -----------------------------------------------------------------------------
# Only loadable settings can be saved: bounds, and saying when the fit is left out
# -----------------------------------------------------------------------------


def test_find_bound_problems():
    from sans_webapp.components.parameters import find_bound_problems

    def update(value, low, high):
        return {'value': value, 'min': low, 'max': high, 'vary': True}

    assert find_bound_problems({'a': update(5, 0, 10), 'b': update(0, 0, 1e300)}) == []
    assert find_bound_problems({'length': update(11111, 10, 1000)}) == [
        'length: value 11111 is outside [10, 1000]'
    ]
    assert find_bound_problems({'a': update(5, 10, 1)}) == ['a: min 10 is above max 1']


def test_parameter_form_rejects_values_outside_their_bounds():
    """The reported case: length 11111 with max 1000 made an unloadable analysis."""
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    app_file = Path(__file__).parent.parent / 'src' / 'sans_webapp' / 'app.py'
    at = AppTest.from_file(str(app_file), default_timeout=90).run()
    at.sidebar.selectbox[0].select('cylinder').run()
    next(b for b in at.button if b.label == 'Load Example').click().run()
    fitter = at.session_state.fitter

    at.number_input(key='value_length').set_value(11111.0)
    next(b for b in at.button if b.label == 'Update Parameters').click().run()

    assert not at.exception
    assert any('within its bounds' in e.value for e in at.error)
    assert fitter.params['length']['value'] == 300.0  # unchanged
    # What is saved can be loaded again
    utils.load_analysis_onto_data(utils.analysis_json(fitter).encode(), fitter.data)


def _stale_fit_app():
    import streamlit as st
    from sans_fitter import SANSFitter

    from sans_webapp.components.analysis_files import render_analysis_files_sidebar

    if 'fitter' not in st.session_state:
        fitter = SANSFitter()
        fitter.load_data('simulated_sans_data.csv')
        fitter.set_model('sphere')
        fitter.set_param('radius', value=40.0, min=5.0, max=200.0, vary=True)
        fitter.fit(engine='bumps', method='amoeba')
        st.session_state.fitter = fitter
        st.session_state.model_selected = True
        st.session_state.data_loaded = True
        st.session_state.fit_completed = True
    render_analysis_files_sidebar()


def test_warns_when_the_saved_analysis_will_not_include_the_fit():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_stale_fit_app, default_timeout=60).run()
    assert len(at.warning) == 0  # the fit is current and will be saved

    at.session_state.fitter.set_param('radius', value=50.0)
    at.run()
    assert len(at.warning) == 1
    assert 'will not include' in at.warning[0].value


def _slider_app():
    import streamlit as st
    from sans_fitter import SANSFitter

    from sans_webapp.components.fit_results import render_fit_results
    from sans_webapp.services.session_state import adopt_fitter, init_session_state

    init_session_state()
    if 'fitter' not in st.session_state or st.session_state.fitter.fit_result is None:
        fitter = SANSFitter()
        fitter.load_data('simulated_sans_data.csv')
        fitter.set_model('sphere')
        fitter.set_param('radius', value=40.0, min=5.0, max=200.0, vary=True)
        fitter.set_param('sld', value=1.0, min=-9.0, max=11.0, vary=True)
        fitter.fit(engine='bumps', method='amoeba')
        adopt_fitter(fitter)
    render_fit_results(st.session_state.fitter, {})


def test_slider_stays_within_the_parameter_bounds():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_slider_app, default_timeout=60).run()
    fitter = at.session_state.fitter
    at.selectbox(key='selected_slider_param').select('radius').run()
    value = fitter.params['radius']['value']
    fitter.set_param('radius', max=value * 1.05)  # the value sits near its upper bound
    at.selectbox(key='selected_slider_param').select('sld').run()
    at.selectbox(key='selected_slider_param').select('radius').run()

    assert not at.exception
    assert at.slider[0].max == pytest.approx(value * 1.05)
    assert at.slider[0].min == pytest.approx(value * 0.8)


def test_slider_handles_negative_values():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_slider_app, default_timeout=60).run()
    at.session_state.fitter.set_param('sld', value=-2.0)
    at.selectbox(key='selected_slider_param').select('radius').run()
    at.selectbox(key='selected_slider_param').select('sld').run()

    assert not at.exception
    assert (at.slider[0].min, at.slider[0].max) == pytest.approx((-2.4, -1.6))
    assert at.slider[0].value == pytest.approx(-2.0)


# -----------------------------------------------------------------------------
# Loading into a session without the analysis's data
# -----------------------------------------------------------------------------


@pytest.fixture(scope='module')
def example_analysis():
    """A fitted sphere analysis made with the bundled 'sphere' example."""
    fitter = examples.load_fitter('sphere')
    fitter.fit(engine='bumps', method='amoeba')
    return utils.analysis_json(fitter).encode()


class TestAnalysisDataSummary:
    def test_describes_the_saved_data(self, fitted):
        summary = utils.analysis_data_summary(utils.analysis_json(fitted).encode())
        assert summary['description'] == f"'{EXAMPLE_DATA}' ({len(fitted.data.x)} points)"
        assert utils.is_analysis_data(fitted.data, summary)
        assert not utils.is_analysis_data(examples.load('sphere'), summary)

    def test_rejects_other_files(self):
        with pytest.raises(ValueError):
            utils.analysis_data_summary(b'not json')
        with pytest.raises(ValueError):
            utils.analysis_data_summary(b'[1, 2]')
        with pytest.raises(ValueError):
            utils.analysis_data_summary(b'{"data": {"label": "x.csv"}}')  # no schema

    def test_analysis_saved_without_data_names_no_dataset(self):
        fitter = SANSFitter()
        fitter.set_model('sphere')  # the sidebar allows a model without data
        assert utils.analysis_data_summary(utils.analysis_json(fitter).encode()) is None

    def test_describes_data_recorded_without_label_or_point_count(self, fitted):
        document = json.loads(utils.analysis_json(fitted))
        del document['data']['label'], document['data']['n_points']
        summary = utils.analysis_data_summary(json.dumps(document).encode())
        assert summary['description'] == "'unnamed dataset'"

    def test_finds_the_example_an_analysis_was_made_with(self, fitted, example_analysis):
        summary = utils.analysis_data_summary(example_analysis)
        assert utils.find_example_for_analysis(summary) == 'sphere'
        own_data = utils.analysis_data_summary(utils.analysis_json(fitted).encode())
        assert utils.find_example_for_analysis(own_data) is None


def _load_app():
    """The Save & Load section with the analysis upload stubbed (AppTest has no uploader)."""
    import streamlit as st
    from sans_fitter import SANSFitter

    from sans_webapp.components import analysis_files
    from sans_webapp.services.session_state import init_session_state

    class Upload:
        def getvalue(self):
            return st.session_state.analysis_contents

    init_session_state()
    if st.session_state.get('with_data') and not st.session_state.data_loaded:
        fitter = SANSFitter()
        fitter.load_data('simulated_sans_data.csv')
        st.session_state.fitter = fitter
        st.session_state.data_loaded = True

    # st is the shared streamlit module: swap the uploader for this render only
    original_uploader = st.file_uploader
    st.file_uploader = lambda *args, **kwargs: Upload()
    try:
        analysis_files.render_analysis_files_sidebar()
    finally:
        st.file_uploader = original_uploader


def _load_session(contents, with_data=False):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_load_app, default_timeout=60)
    at.session_state['analysis_contents'] = contents
    at.session_state['with_data'] = with_data
    return at.run()


def test_example_analysis_loads_its_data_in_a_fresh_session(example_analysis):
    at = _load_session(example_analysis)
    assert "saved with '100nmSpheresNodQ.txt' (150 points)" in at.info[0].value
    assert [b.label for b in at.button] == ["Load example 'sphere' and apply"]

    at.button[0].click().run()
    assert not at.exception
    fitter = at.session_state.fitter
    assert fitter.model_name == 'sphere'
    assert len(fitter.data.x) == 150
    assert at.session_state.data_loaded is True
    assert at.session_state.fit_completed is True  # the saved fit came back


def test_analysis_of_uploaded_data_names_the_data_it_needs(fitted):
    at = _load_session(utils.analysis_json(fitted).encode())
    assert f"saved with '{EXAMPLE_DATA}'" in at.info[0].value
    assert len(at.button) == 0  # nothing to apply it to yet


def test_other_loaded_data_is_pointed_out_but_can_be_used(example_analysis):
    at = _load_session(example_analysis, with_data=True)
    assert 'not the loaded data' in at.info[0].value
    labels = [b.label for b in at.button]
    assert labels == ["Load example 'sphere' and apply", 'Apply to loaded data']

    at.button[1].click().run()
    assert not at.exception
    assert at.session_state.fitter.model_name == 'sphere'
    assert at.session_state.fit_completed is False  # setup only: different data


def test_analysis_without_data_asks_for_data_then_applies_to_it():
    fitter = SANSFitter()
    fitter.set_model('cylinder')
    contents = utils.analysis_json(fitter).encode()

    at = _load_session(contents)
    assert 'names no dataset' in at.info[0].value
    assert len(at.button) == 0

    at = _load_session(contents, with_data=True)
    assert len(at.info) == 0
    assert [b.label for b in at.button] == ['Apply to loaded data']
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state.fitter.model_name == 'cylinder'


# -----------------------------------------------------------------------------
# Every parameter write respects the bounds
# -----------------------------------------------------------------------------


@pytest.fixture
def sphere_fitter():
    fitter = SANSFitter()
    fitter.load_data(EXAMPLE_DATA)
    fitter.set_model('sphere')
    return fitter


class TestSetParamWithinBounds:
    def test_accepts_settings_within_bounds(self, sphere_fitter):
        utils.set_param_within_bounds(sphere_fitter, 'radius', value=40.0, min=5.0, vary=True)
        assert sphere_fitter.params['radius']['value'] == 40.0
        assert sphere_fitter.params['radius']['min'] == 5.0
        assert sphere_fitter.params['radius']['vary'] is True

    @pytest.mark.parametrize(
        'settings',
        [{'value': 11111.0}, {'max': 10.0}, {'min': 600.0}, {'min': 100.0, 'max': 10.0}],
    )
    def test_refuses_settings_outside_bounds_and_leaves_the_fitter(self, sphere_fitter, settings):
        before = dict(sphere_fitter.params['radius'])
        with pytest.raises(ValueError):
            utils.set_param_within_bounds(sphere_fitter, 'radius', **settings)
        assert sphere_fitter.params['radius'] == before


def _call_parameter_tool(fitter, mock_session_state, tool, **kwargs):
    from sans_webapp import mcp_server

    mcp_server.set_fitter(fitter)
    mock_session_state._data['fitter'] = fitter
    with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
        mock_st.session_state = mock_session_state
        return getattr(mcp_server, tool)(**kwargs)


def test_set_parameter_tool_refuses_values_outside_bounds(sphere_fitter, mock_session_state):
    """The review's reproduction: the AI tool could write radius = 11111 (max 550)."""
    result = _call_parameter_tool(
        sphere_fitter, mock_session_state, 'set_parameter', name='radius', value=11111.0
    )
    assert result.startswith("Error setting parameter 'radius'")
    assert sphere_fitter.params['radius']['value'] == 50.0
    # What is saved can be loaded again
    utils.load_analysis_onto_data(utils.analysis_json(sphere_fitter).encode(), sphere_fitter.data)


def test_set_multiple_parameters_tool_applies_valid_and_rejects_invalid(
    sphere_fitter, mock_session_state
):
    result = _call_parameter_tool(
        sphere_fitter,
        mock_session_state,
        'set_multiple_parameters',
        parameters={'radius': {'value': 11111.0}, 'scale': {'value': 0.5}},
    )
    assert 'radius: REJECTED' in result
    assert sphere_fitter.params['radius']['value'] == 50.0
    assert sphere_fitter.params['scale']['value'] == 0.5


# -----------------------------------------------------------------------------
# Uploaded data is recorded by name, not by a temporary path
# -----------------------------------------------------------------------------


def test_uploaded_data_is_recorded_by_name_without_a_dead_path():
    with open(EXAMPLE_DATA, 'rb') as file:
        data = utils.load_uploaded_data('my_sample.csv', file.read())
    fitter = SANSFitter()
    fitter.set_data(data)
    fitter.set_model('sphere')

    section = json.loads(utils.analysis_json(fitter))['data']
    assert section['label'] == 'my_sample.csv'
    assert 'path_absolute' not in section
    report = utils.report_html(fitter)
    assert '<td>my_sample.csv</td>' in report
