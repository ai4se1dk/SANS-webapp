"""
Tests for loading sans-fitter's bundled examples: the sidebar picker, the
shared load_example() helper and the load-example MCP tool.
"""

from unittest.mock import patch

import pytest
from sans_fitter import SANSFitter, examples
from streamlit.testing.v1 import AppTest

from sans_webapp.services import session_state


class AttrDict(dict):
    """Stand-in for st.session_state: a dict that also takes attribute access."""

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


def test_load_example_replaces_the_fitter_with_the_configured_example():
    state = AttrDict(fitter=SANSFitter(), value_radius=1.0, fit_completed=True)
    with patch.object(session_state.st, 'session_state', state):
        fitter = session_state.load_example('silica_spheres')

    example = examples.get_example('silica_spheres')
    assert state.fitter is fitter
    assert fitter.model_name == example.model
    assert fitter.params['radius']['value'] == example.params['radius']['value']
    assert state.data_loaded is True
    assert state.model_selected is True
    assert state.current_model == example.model
    assert state.fit_completed is False
    assert 'value_radius' not in state  # widgets re-initialize from the new fitter


def test_unknown_example_raises():
    with pytest.raises(KeyError):
        session_state.load_example('no_such_example')


# -----------------------------------------------------------------------------
# Sidebar picker
# -----------------------------------------------------------------------------


def _picker_app():
    import streamlit as st
    from sans_fitter import SANSFitter

    from sans_webapp.components.sidebar import render_data_upload_sidebar

    if 'fitter' not in st.session_state:
        st.session_state.fitter = SANSFitter()
        st.session_state.data_loaded = False
        st.session_state.expand_data_upload = True
        st.session_state.last_uploaded_file_id = None
    render_data_upload_sidebar()


def test_picker_describes_the_selected_example():
    at = AppTest.from_function(_picker_app, default_timeout=30).run()
    assert not at.exception
    picker = at.sidebar.selectbox[0]
    assert picker.value == 'sphere'
    assert picker.options == examples.list_examples()
    captions = [c.value for c in at.sidebar.caption]
    assert examples.get_example('sphere').description in captions

    picker.select('silica_spheres').run()
    captions = [c.value for c in at.sidebar.caption]
    assert examples.get_example('silica_spheres').description in captions


def test_load_example_button_loads_data_model_and_parameters():
    at = AppTest.from_function(_picker_app, default_timeout=30).run()
    at.sidebar.selectbox[0].select('cylinder').run()
    at.sidebar.button[0].click().run()

    assert not at.exception
    assert at.session_state.fitter.model_name == 'cylinder'
    assert at.session_state.data_loaded is True
    assert at.session_state.model_selected is True
    assert at.session_state.expand_parameters is True


# -----------------------------------------------------------------------------
# load-example MCP tool
# -----------------------------------------------------------------------------


def _call_tool(state, name):
    from sans_webapp.mcp_server import get_fitter, load_example

    with (
        patch.object(session_state.st, 'session_state', state),
        patch('sans_webapp.services.mcp_state_bridge.st') as bridge_st,
    ):
        bridge_st.session_state = state
        return load_example(name), get_fitter()


def test_tool_loads_the_example_everywhere():
    state = AttrDict(fitter=SANSFitter(), ai_tools_enabled=True)
    result, mcp_fitter = _call_tool(state, 'cylinder')

    assert result.startswith("Loaded example 'cylinder'")
    assert state.fitter.model_name == 'cylinder'
    assert mcp_fitter is state.fitter  # the MCP tools act on the new fitter
    assert state.needs_rerun is True


def test_tool_reports_unknown_examples():
    state = AttrDict(fitter=SANSFitter(), ai_tools_enabled=True)
    result, _ = _call_tool(state, 'no_such_example')
    assert result.startswith('Error loading example')


def test_tool_respects_disabled_ai_tools():
    old_fitter = SANSFitter()
    state = AttrDict(fitter=old_fitter, ai_tools_enabled=False)
    result, _ = _call_tool(state, 'cylinder')
    assert 'disabled' in result
    assert state.fitter is old_fitter
