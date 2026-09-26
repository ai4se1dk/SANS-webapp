"""
Save & Load component for SANS webapp.

Downloads the analysis (sans-fitter's JSON analysis file) and a shareable HTML
report, and applies a saved analysis to the loaded data.
"""

import streamlit as st
from sans_fitter import examples

from sans_webapp.sans_analysis_utils import (
    analysis_data_summary,
    analysis_json,
    find_example_for_analysis,
    fit_is_current,
    is_analysis_data,
    load_analysis_onto_data,
    report_html,
)
from sans_webapp.services.session_state import adopt_fitter
from sans_webapp.ui_constants import (
    ANALYSIS_DATA_DIFFERENT,
    ANALYSIS_DATA_NOT_LOADED,
    ANALYSIS_FIT_NOT_SAVED_WARNING,
    ANALYSIS_NEEDS_DATA_INFO,
    ANALYSIS_SAVE_CAPTION,
    ANALYSIS_UPLOAD_HELP,
    ANALYSIS_UPLOAD_LABEL,
    APPLY_ANALYSIS_BUTTON,
    DOWNLOAD_ANALYSIS_BUTTON,
    DOWNLOAD_REPORT_BUTTON,
    LOAD_EXAMPLE_AND_APPLY_BUTTON,
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
    if st.session_state.get('fit_completed') and not fit_is_current(fitter):
        st.warning(ANALYSIS_FIT_NOT_SAVED_WARNING)


def _render_load() -> None:
    uploaded = st.file_uploader(
        ANALYSIS_UPLOAD_LABEL, type=['json'], help=ANALYSIS_UPLOAD_HELP, key='analysis_upload'
    )
    data_loaded = st.session_state.data_loaded
    if uploaded is None:
        if not data_loaded:
            st.caption(ANALYSIS_NEEDS_DATA_INFO)
        return

    contents = uploaded.getvalue()
    try:
        summary = analysis_data_summary(contents)
    except ValueError as e:
        st.error(f'Could not read the analysis: {e}')
        return

    # Say which data the analysis needs unless it is the data already loaded
    has_its_data = data_loaded and is_analysis_data(st.session_state.fitter.data, summary)
    if not data_loaded:
        st.info(ANALYSIS_DATA_NOT_LOADED.format(**summary))
    elif not has_its_data:
        st.info(ANALYSIS_DATA_DIFFERENT.format(**summary))

    example = find_example_for_analysis(summary)
    if example is not None and not has_its_data:
        if st.button(LOAD_EXAMPLE_AND_APPLY_BUTTON.format(name=example)):
            _apply(contents, examples.load(example))
    if data_loaded and st.button(APPLY_ANALYSIS_BUTTON):
        _apply(contents, st.session_state.fitter.data)


def _apply(contents: bytes, data) -> None:
    """Apply the analysis to *data* and make the result the app's fitter."""
    try:
        fitter = load_analysis_onto_data(contents, data)
    except Exception as e:
        st.error(f'Could not load the analysis: {e}')
        return
    adopt_fitter(fitter)
    st.session_state.expand_data_upload = False
    st.session_state.expand_model_selection = False
    st.session_state.expand_parameters = True
    st.toast(SUCCESS_ANALYSIS_LOADED_WITH_FIT if fitter.fit_result else SUCCESS_ANALYSIS_LOADED)
    st.rerun()
