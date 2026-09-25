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


def test_defaults_to_the_fitters_setting(app):
    assert not app.exception
    assert app.selectbox[0].value == 'data'
    assert len(app.number_input) == 0  # the width only applies to pinhole


def test_choosing_pinhole_applies_it_with_the_default_width(app):
    app.selectbox[0].select('pinhole').run()
    assert app.session_state.fitter.get_resolution()['mode'] == 'pinhole'
    assert app.session_state.fitter.get_resolution()['dq_over_q'] == pytest.approx(0.05)

    app.number_input[0].set_value(0.1).run()
    assert app.session_state.fitter.get_resolution()['dq_over_q'] == pytest.approx(0.1)

    app.selectbox[0].select('none').run()
    assert app.session_state.fitter.get_resolution()['mode'] == 'none'
    assert len(app.number_input) == 0


def test_change_made_elsewhere_shows_on_the_next_run(app):
    app.session_state.fitter.set_resolution('pinhole', dq_over_q=0.2)
    app.run()
    assert app.selectbox[0].value == 'pinhole'
    assert app.number_input[0].value == pytest.approx(0.2)


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


def test_tool_respects_disabled_ai_tools(fitter, mock_session_state):
    mock_session_state.ai_tools_enabled = False
    result = _call_tool(fitter, mock_session_state, mode='none')
    assert 'disabled' in result
    assert fitter.get_resolution()['mode'] == 'data'
