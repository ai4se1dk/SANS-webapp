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
    render_ai_chat_column,
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


def init_mcp_and_ai() -> None:
    """Initialize MCP references and pre-warm Claude client if an API key exists.

    Calls into `sans_webapp.mcp_server` to set the current fitter and session accessor.
    Attempts to create the Claude client singleton if an API key is configured in
    `st.session_state.chat_api_key` or in the `ANTHROPIC_API_KEY` environment variable.
    Errors are captured in `st.session_state.ai_client_error` to avoid breaking UI startup.
    """
    try:
        from sans_webapp.mcp_server import set_fitter, set_state_accessor
        from sans_webapp.services.claude_mcp_client import get_claude_client

        # Provide the MCP server with direct access to the current fitter and session
        set_fitter(st.session_state.fitter)
        set_state_accessor(st.session_state)

        # Attempt to initialize the Claude client if API key is configured
        api_key = st.session_state.get('chat_api_key') or __import__('os').environ.get(
            'ANTHROPIC_API_KEY'
        )
        if api_key:
            try:
                # Create the singleton client (may raise if key invalid)
                get_claude_client(api_key)
            except Exception as e:  # pragma: no cover - defensive logging
                # Store error for debugging in session state but do not interrupt UI
                st.session_state.ai_client_error = str(e)
    except Exception as e:  # pragma: no cover - defensive logging
        # Non-fatal: continue running the app even if MCP initialization fails
        print(f'Warning: failed to initialize MCP/AI client: {e}')


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

    # Inject custom CSS and JS for resizable AI chat column
    st.markdown(
        """
        <style>
        /* Make the right column (AI chat) sticky and resizable */
        div[data-testid="stHorizontalBlock"] {
            position: relative;
        }
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
            position: sticky;
            top: 3.5rem;
            height: fit-content;
            max-height: calc(100vh - 4rem);
            overflow-y: auto;
            align-self: flex-start;
            min-width: 250px;
            max-width: 50%;
            border-left: 3px solid #e0e0e0;
            padding-left: 10px;
            transition: none;
        }
        div[data-testid="stHorizontalBlock"] > div:nth-child(2):hover {
            border-left-color: #1f77b4;
        }
        /* Resize handle */
        .resize-handle {
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 6px;
            cursor: col-resize;
            background: transparent;
            z-index: 1000;
        }
        .resize-handle:hover, .resize-handle.dragging {
            background: rgba(31, 119, 180, 0.3);
        }
        </style>
        <script>
        (function() {
            // Wait for Streamlit to render
            const initResizable = () => {
                const container = document.querySelector('[data-testid="stHorizontalBlock"]');
                if (!container) {
                    setTimeout(initResizable, 100);
                    return;
                }

                const leftCol = container.children[0];
                const rightCol = container.children[1];

                if (!leftCol || !rightCol || rightCol.querySelector('.resize-handle')) return;

                // Create resize handle
                const handle = document.createElement('div');
                handle.className = 'resize-handle';
                rightCol.style.position = 'relative';
                rightCol.insertBefore(handle, rightCol.firstChild);

                let startX, startWidth, containerWidth;

                handle.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    startX = e.clientX;
                    startWidth = rightCol.offsetWidth;
                    containerWidth = container.offsetWidth;
                    handle.classList.add('dragging');

                    const onMouseMove = (e) => {
                        const delta = startX - e.clientX;
                        const newWidth = Math.min(Math.max(startWidth + delta, 250), containerWidth * 0.5);
                        const newLeftWidth = containerWidth - newWidth - 20;

                        rightCol.style.flex = 'none';
                        rightCol.style.width = newWidth + 'px';
                        leftCol.style.flex = 'none';
                        leftCol.style.width = newLeftWidth + 'px';
                    };

                    const onMouseUp = () => {
                        handle.classList.remove('dragging');
                        document.removeEventListener('mousemove', onMouseMove);
                        document.removeEventListener('mouseup', onMouseUp);
                    };

                    document.addEventListener('mousemove', onMouseMove);
                    document.addEventListener('mouseup', onMouseUp);
                });
            };

            // Initialize after a short delay
            setTimeout(initResizable, 500);

            // Re-initialize on Streamlit reruns
            const observer = new MutationObserver(() => {
                setTimeout(initResizable, 100);
            });
            observer.observe(document.body, { childList: true, subtree: true });
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

    # Initialize session state
    init_session_state()

    # Initialize MCP server references and AI client if available
    # Call module-level helper
    init_mcp_and_ai()

    # Call initialization helper (kept inline for deterministic startup)
    init_mcp_and_ai()

    # Sidebar for controls
    st.sidebar.header(SIDEBAR_CONTROLS_HEADER)

    render_data_upload_sidebar()
    render_model_selection_sidebar()

    # Create two-column layout: main content (70%) and AI chat (30%)
    col1, col2 = st.columns([0.7, 0.3])

    # AI Chat in the right column
    with col2:
        render_ai_chat_column(st.session_state.chat_api_key, st.session_state.fitter)

    # Main content in the left column
    with col1:
        # Main content area - handle case when data is not loaded
        if not st.session_state.data_loaded:
            st.info(INFO_NO_DATA)
            st.markdown(DATA_FORMAT_HELP)
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


if __name__ == '__main__':
    main()
