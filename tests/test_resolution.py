"""
Tests for the resolution (smearing) controls and the set-resolution MCP tool.
"""

from unittest.mock import patch

import pytest
from sans_fitter import SANSFitter
from streamlit.testing.v1 import AppTest

EXAMPLE_DATA = 'simulated_sans_data.csv'


@pytest.fixture
def fitter():
    fitter = SANSFitter()
    fitter.load_data(EXAMPLE_DATA)
    fitter.set_model('sphere')
    return fitter


# -----------------------------------------------------------------------------
# Sidebar controls
# -----------------------------------------------------------------------------


def _controls_app():
    import streamlit as st
    from sans_fitter import SANSFitter

    from sans_webapp.components.sidebar import render_resolution_controls

    if 'fitter' not in st.session_state:
        fitter = SANSFitter()
        fitter.load_data('simulated_sans_data.csv')
        st.session_state.fitter = fitter
    render_resolution_controls(st.session_state.fitter)


@pytest.fixture
def app():
    return AppTest.from_function(_controls_app, default_timeout=30).run()


def _assert_shows(app, mode, dq_over_q=None):
    """The controls and the fitter agree on *mode* (and the pinhole width)."""
    resolution = app.session_state.fitter.get_resolution()
    assert resolution['mode'] == mode
    assert app.selectbox[0].value == mode
    if mode == 'pinhole':
        assert resolution['dq_over_q'] == pytest.approx(dq_over_q)
        assert app.number_input[0].value == pytest.approx(dq_over_q)
    else:
        assert len(app.number_input) == 0  # the width only applies to pinhole


def test_defaults_to_the_fitters_setting(app):
    assert not app.exception
    _assert_shows(app, 'data')


def test_consecutive_mode_changes_all_apply(app):
    app.selectbox[0].select('none').run()
    _assert_shows(app, 'none')
    app.selectbox[0].select('pinhole').run()
    _assert_shows(app, 'pinhole', 0.05)
    app.selectbox[0].select('data').run()
    _assert_shows(app, 'data')


def test_consecutive_width_edits_all_apply(app):
    app.selectbox[0].select('pinhole').run()
    app.number_input[0].set_value(0.1).run()
    _assert_shows(app, 'pinhole', 0.1)
    app.number_input[0].set_value(0.2).run()
    _assert_shows(app, 'pinhole', 0.2)
    app.number_input[0].set_value(0.3).run()
    _assert_shows(app, 'pinhole', 0.3)


def test_pinhole_width_is_kept_across_other_modes(app):
    app.selectbox[0].select('pinhole').run()
    app.number_input[0].set_value(0.2).run()
    app.selectbox[0].select('none').run()
    _assert_shows(app, 'none')
    app.selectbox[0].select('pinhole').run()
    _assert_shows(app, 'pinhole', 0.2)


def test_change_made_elsewhere_right_after_an_edit_is_kept(app):
    app.selectbox[0].select('none').run()
    app.session_state.fitter.set_resolution('data')
    app.run()
    _assert_shows(app, 'data')

    app.selectbox[0].select('pinhole').run()
    app.session_state.fitter.set_resolution('pinhole', dq_over_q=0.2)
    app.run()
    _assert_shows(app, 'pinhole', 0.2)


def test_rejected_width_is_reported_and_leaves_the_fitter_alone(app):
    app.selectbox[0].select('pinhole').run()
    app.number_input[0].set_value(0.0).run()
    assert not app.exception
    assert len(app.error) == 1
    _assert_shows(app, 'pinhole', 0.05)


def test_mode_without_a_control_is_shown_and_left_alone(app):
    app.session_state.fitter.set_resolution('slit', slit_length=0.05)
    app.run()
    assert not app.exception
    assert app.selectbox[0].value is None
    assert 'slit' in app.caption[0].value
    assert app.session_state.fitter.get_resolution()['mode'] == 'slit'


# -----------------------------------------------------------------------------
# set-resolution MCP tool
# -----------------------------------------------------------------------------


def _call_tool(fitter, session_state, **kwargs):
    from sans_webapp.mcp_server import set_fitter, set_resolution

    set_fitter(fitter)
    with patch('sans_webapp.services.mcp_state_bridge.st') as mock_st:
        mock_st.session_state = session_state
        return set_resolution(**kwargs)


def test_tool_sets_pinhole_and_requests_a_rerun(fitter, mock_session_state):
    result = _call_tool(fitter, mock_session_state, mode='pinhole', dq_over_q=0.05)
    assert 'pinhole' in result and '0.05' in result
    assert fitter.get_resolution() == {
        'mode': 'pinhole',
        'dq_over_q': 0.05,
        'slit_length': None,
        'slit_width': None,
    }
    assert mock_session_state.needs_rerun is True


def test_tool_reports_invalid_settings_without_changing_the_fitter(fitter, mock_session_state):
    result = _call_tool(fitter, mock_session_state, mode='pinhole')
    assert result.startswith('Error setting resolution')
    assert fitter.get_resolution()['mode'] == 'data'


@pytest.mark.parametrize('dq_over_q', [0.0005, 0.001, 1.0, 1.1])
def test_any_width_the_tool_sets_is_shown_unchanged(app, mock_session_state, dq_over_q):
    result = _call_tool(
        app.session_state.fitter, mock_session_state, mode='pinhole', dq_over_q=dq_over_q
    )
    assert not result.startswith('Error')
    app.run()
    assert not app.exception
    _assert_shows(app, 'pinhole', dq_over_q)


def test_tool_respects_disabled_ai_tools(fitter, mock_session_state):
    mock_session_state.ai_tools_enabled = False
    result = _call_tool(fitter, mock_session_state, mode='none')
    assert 'disabled' in result
    assert fitter.get_resolution()['mode'] == 'data'
