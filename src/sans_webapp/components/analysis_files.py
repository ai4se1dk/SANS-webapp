"""
Save & Load component for SANS webapp.

Downloads the analysis (sans-fitter's JSON analysis file) and a shareable HTML
report, and applies a saved analysis to the loaded data.
"""

import streamlit as st

from sans_webapp.sans_analysis_utils import analysis_json, load_analysis_onto_data, report_html
from sans_webapp.services.session_state import adopt_fitter
from sans_webapp.ui_constants import (
    ANALYSIS_NEEDS_DATA_INFO,
    ANALYSIS_SAVE_CAPTION,
    ANALYSIS_UPLOAD_HELP,
    ANALYSIS_UPLOAD_LABEL,
    APPLY_ANALYSIS_BUTTON,
    DOWNLOAD_ANALYSIS_BUTTON,
    DOWNLOAD_REPORT_BUTTON,
    SIDEBAR_ANALYSIS_FILES_HEADER,
    SUCCESS_ANALYSIS_LOADED,
    SUCCESS_ANALYSIS_LOADED_WITH_FIT,
)


def render_analysis_files_sidebar() -> None:
    """Render the Save & Load controls in the sidebar as a collapsible section."""
    with st.sidebar.expander(SIDEBAR_ANALYSIS_FILES_HEADER, expanded=False):
        _render_downloads()
        st.markdown('---')
        _render_load()


def _render_downloads() -> None:
    if not st.session_state.model_selected:
        return
    fitter = st.session_state.fitter
    name = fitter.model_name
    # Callables: the files are only built when a button is clicked
    st.download_button(
        DOWNLOAD_ANALYSIS_BUTTON,
        data=lambda: analysis_json(fitter),
        file_name=f'{name}_analysis.json',
        mime='application/json',
    )
    st.download_button(
        DOWNLOAD_REPORT_BUTTON,
        data=lambda: report_html(fitter),
        file_name=f'{name}_report.html',
        mime='text/html',
    )
    st.caption(ANALYSIS_SAVE_CAPTION)


def _render_load() -> None:
    uploaded = st.file_uploader(
        ANALYSIS_UPLOAD_LABEL, type=['json'], help=ANALYSIS_UPLOAD_HELP, key='analysis_upload'
    )
    if not st.session_state.data_loaded:
        st.caption(ANALYSIS_NEEDS_DATA_INFO)
        return
    if uploaded is None or not st.button(APPLY_ANALYSIS_BUTTON):
        return
    try:
        fitter = load_analysis_onto_data(uploaded.getvalue(), st.session_state.fitter.data)
    except Exception as e:
        st.error(f'Could not load the analysis: {e}')
        return
    adopt_fitter(fitter)
    st.session_state.expand_parameters = True
    st.toast(SUCCESS_ANALYSIS_LOADED_WITH_FIT if fitter.fit_result else SUCCESS_ANALYSIS_LOADED)
    st.rerun()
