"""
SANS Data Analysis Web Application

A Streamlit-based web application for Small Angle Neutron Scattering (SANS) data analysis.
Features include data upload, model selection (manual and AI-assisted), parameter fitting,
and interactive visualization.

This is the main orchestration module. Business logic and UI components are organized in:
- components/: UI rendering components (sidebar, parameters, data_preview, fit_results)
- services/: Business logic services (ai_chat, session_state)
- sans_types.py: TypedDict definitions
- ui_constants.py: All UI string constants
"""

from typing import cast

import streamlit as st
from sans_fitter import get_all_models  # noqa: F401 - re-exported for backwards compatibility

from sans_webapp.components.data_preview import render_data_preview
from sans_webapp.components.fit_results import render_fit_results
from sans_webapp.components.parameters import (
    apply_param_updates,
    apply_pd_updates,
    render_parameter_configuration,
)
from sans_webapp.components.sidebar import (
    render_ai_chat_sidebar,
    render_data_upload_sidebar,
    render_model_selection_sidebar,
)
from sans_webapp.sans_analysis_utils import (  # noqa: F401 - re-exported for backwards compatibility
    analyze_data_for_ai_suggestion,
    plot_data_and_fit,
    suggest_models_simple,
)
from sans_webapp.sans_types import FitResult, ParamUpdate
from sans_webapp.services.ai_chat import (
    suggest_models_ai,  # noqa: F401 - re-exported for backwards compatibility
)
from sans_webapp.services.session_state import (
    clamp_for_display,  # noqa: F401 - re-exported for backwards compatibility
    init_session_state,
)
from sans_webapp.ui_constants import (
    APP_LAYOUT,
    APP_PAGE_ICON,
    APP_PAGE_TITLE,
    APP_SIDEBAR_STATE,
    APP_SUBTITLE,
    APP_TITLE,
    DATA_FORMAT_HELP,
    FIT_ENGINE_HELP,
    FIT_ENGINE_LABEL,
    FIT_ENGINE_OPTIONS,
    FIT_METHOD_BUMPS,
    FIT_METHOD_HELP_BUMPS,
    FIT_METHOD_HELP_LMFIT,
    FIT_METHOD_LABEL,
    FIT_METHOD_LMFIT,
    FIT_RUN_BUTTON,
    INFO_NO_DATA,
    SIDEBAR_CONTROLS_HEADER,
    SIDEBAR_FITTING_HEADER,
    SUCCESS_FIT_COMPLETED,
    WARNING_NO_VARY,
)


def render_fitting_sidebar(param_updates: dict[str, ParamUpdate]) -> None:
    """Render the fitting controls in the sidebar with Run Fit button always visible."""
    fitter = st.session_state.fitter

    # Engine/method selection in collapsible section
    with st.sidebar.expander(SIDEBAR_FITTING_HEADER, expanded=st.session_state.expand_fitting):
        engine = st.selectbox(
            FIT_ENGINE_LABEL, FIT_ENGINE_OPTIONS, help=FIT_ENGINE_HELP, key='fit_engine'
        )

        if engine == 'bumps':
            st.selectbox(
                FIT_METHOD_LABEL,
                FIT_METHOD_BUMPS,
                help=FIT_METHOD_HELP_BUMPS,
                key='fit_method_bumps',
            )
        else:
            st.selectbox(
                FIT_METHOD_LABEL,
                FIT_METHOD_LMFIT,
                help=FIT_METHOD_HELP_LMFIT,
                key='fit_method_lmfit',
            )

    # Run Fit button always visible outside the expander
    if st.sidebar.button(FIT_RUN_BUTTON, type='primary'):
        engine = st.session_state.get('fit_engine', 'bumps')
        if engine == 'bumps':
            method = st.session_state.get('fit_method_bumps', 'amoeba')
        else:
            method = st.session_state.get('fit_method_lmfit', 'leastsq')

        # Apply current parameter settings before fitting
        apply_param_updates(fitter, param_updates)

        # Apply polydispersity settings if model supports it
        if fitter.supports_polydispersity():
            # Sync enable state from session
            pd_enabled = st.session_state.get('pd_enabled', False)
            fitter.enable_polydispersity(pd_enabled)

            # Apply PD parameters if enabled and valid for current model
            if pd_enabled and 'pd_updates' in st.session_state:
                current_pd_params = set(fitter.get_polydisperse_parameters())
                stored_params = set(st.session_state.pd_updates.keys())
                # Only apply if stored params match current model's PD params
                if stored_params == current_pd_params:
                    apply_pd_updates(fitter, st.session_state.pd_updates)

        with st.spinner(f'Fitting with {engine}/{method}...'):
            try:
                any_vary = any(p['vary'] for p in fitter.params.values())
                if not any_vary:
                    st.sidebar.warning(WARNING_NO_VARY)
                else:
                    result = fitter.fit(engine=engine, method=method)
                    st.session_state.fit_completed = True
                    st.session_state.fit_result = cast(FitResult, result)
                    st.sidebar.success(SUCCESS_FIT_COMPLETED)
            except Exception as e:
                st.sidebar.error(f'Fitting error: {str(e)}')


def main() -> None:
    """Main Streamlit application."""
    st.set_page_config(
        page_title=APP_PAGE_TITLE,
        page_icon=APP_PAGE_ICON,
        layout=APP_LAYOUT,
        initial_sidebar_state=APP_SIDEBAR_STATE,
    )

    st.title(APP_TITLE)
    st.markdown(APP_SUBTITLE)

    # Initialize session state
    init_session_state()

    # Sidebar for controls
    st.sidebar.header(SIDEBAR_CONTROLS_HEADER)

    render_data_upload_sidebar()
    render_model_selection_sidebar()

    # Main content area - handle case when data is not loaded
    if not st.session_state.data_loaded:
        st.info(INFO_NO_DATA)
        st.markdown(DATA_FORMAT_HELP)
        render_ai_chat_sidebar(st.session_state.chat_api_key, st.session_state.fitter)
        return

    # Data is loaded - render data preview
    render_data_preview(st.session_state.fitter)

    # Parameter Configuration
    if st.session_state.model_selected:
        param_updates = render_parameter_configuration(st.session_state.fitter)

        # Fitting Section (in sidebar)
        render_fitting_sidebar(param_updates)

        # Display fit results
        if st.session_state.fit_completed:
            render_fit_results(st.session_state.fitter, param_updates)

    # Render AI Chat in left sidebar (at the bottom)
    render_ai_chat_sidebar(st.session_state.chat_api_key, st.session_state.fitter)


if __name__ == '__main__':
    main()
