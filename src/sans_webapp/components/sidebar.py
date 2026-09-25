"""
Sidebar components for SANS webapp.

Contains rendering functions for the sidebar sections:
- Data upload
- Model selection
- AI chat
"""

import os
import tempfile
from importlib.resources import files
from pathlib import Path
from typing import Optional

import streamlit as st
from sans_fitter import SANSFitter, get_all_models

from sans_webapp.services.ai_chat import (
    response_requests_enable_tools,
    send_chat_message,
    suggest_models_ai,
)
from sans_webapp.ui_constants import (
    AI_ASSISTED_HEADER,
    AI_CHAT_CLEAR_BUTTON,
    AI_CHAT_DESCRIPTION,
    AI_CHAT_EMPTY_CAPTION,
    AI_CHAT_HISTORY_HEADER,
    AI_CHAT_INPUT_PLACEHOLDER,
    AI_CHAT_SEND_BUTTON,
    AI_CHAT_SIDEBAR_HEADER,
    AI_CHAT_THINKING,
    AI_KEY_HELP,
    AI_KEY_LABEL,
    AI_SUGGESTIONS_BUTTON,
    AI_SUGGESTIONS_HEADER,
    AI_SUGGESTIONS_SELECT_LABEL,
    CHAT_HISTORY_HEIGHT,
    CHAT_INPUT_HEIGHT,
    ERROR_EXAMPLE_NOT_FOUND,
    EXAMPLE_DATA_BUTTON,
    EXAMPLE_DATA_FILE,
    LOAD_MODEL_BUTTON,
    MODEL_SELECT_HELP,
    MODEL_SELECT_LABEL,
    Q_RANGE_APPLY_BUTTON,
    Q_RANGE_HEADER,
    Q_RANGE_HELP,
    Q_RANGE_MAX_LABEL,
    Q_RANGE_MIN_LABEL,
    Q_RANGE_RESET_BUTTON,
    RESOLUTION_DQ_DEFAULT,
    RESOLUTION_DQ_HELP,
    RESOLUTION_DQ_LABEL,
    RESOLUTION_HEADER,
    RESOLUTION_MODE_HELP,
    RESOLUTION_MODE_LABEL,
    RESOLUTION_MODES,
    RESOLUTION_OTHER_MODE_CAPTION,
    SELECTION_METHOD_HELP,
    SELECTION_METHOD_LABEL,
    SELECTION_METHOD_OPTIONS,
    SIDEBAR_DATA_UPLOAD_HEADER,
    SIDEBAR_MODEL_SELECTION_HEADER,
    SPINNER_ANALYZING_DATA,
    SUCCESS_AI_SUGGESTIONS_PREFIX,
    SUCCESS_AI_SUGGESTIONS_SUFFIX,
    SUCCESS_DATA_UPLOADED,
    SUCCESS_EXAMPLE_LOADED,
    SUCCESS_MODEL_LOADED_PREFIX,
    SUCCESS_MODEL_LOADED_SUFFIX,
    SUCCESS_Q_RANGE_RESET,
    SUCCESS_Q_RANGE_UPDATED,
    UPLOAD_HELP,
    UPLOAD_LABEL,
    UPLOAD_TYPES,
    WARNING_LOAD_DATA_FIRST,
    WARNING_NO_SUGGESTIONS,
)


def _get_example_data_path() -> Path | None:
    """Get the path to the example data file bundled with the package."""
    # First, try to find it relative to the package
    try:
        package_files = files('sans_webapp')
        example_path = package_files / 'data' / EXAMPLE_DATA_FILE
        if hasattr(example_path, 'is_file') and example_path.is_file():
            return Path(str(example_path))
    except (TypeError, FileNotFoundError):
        pass

    # Fallback: check current working directory
    cwd_path = Path.cwd() / EXAMPLE_DATA_FILE
    if cwd_path.exists():
        return cwd_path

    # Fallback: check parent directories (for development)
    for parent in [Path.cwd()] + list(Path.cwd().parents)[:3]:
        candidate = parent / EXAMPLE_DATA_FILE
        if candidate.exists():
            return candidate

    return None


# Session keys of the resolution widgets (see render_resolution_controls)
RESOLUTION_MODE_KEY = 'resolution_mode'
RESOLUTION_DQ_KEY = 'resolution_dq_over_q'
RESOLUTION_ERROR_KEY = 'resolution_error'

# Session keys that belong to the fit Q-range widgets (see render_q_range_controls)
Q_RANGE_WIDGET_KEYS = ('fit_qmin', 'fit_qmax')

# Prefixes of the per-parameter widget keys that must be cleared on a model change
_PARAMETER_WIDGET_PREFIXES = (
    'value_',
    'min_',
    'max_',
    'vary_',
    'pd_width_',
    'pd_n_',
    'pd_type_',
    'pd_vary_',
)
# Aggregate keys that describe the previous model's parameter/PD configuration
_PARAMETER_STATE_KEYS = ('param_updates', 'pd_updates', 'pd_enabled')


def _reset_after_data_load() -> None:
    """Drop state that described the previous dataset (fit result, Q range widgets)."""
    st.session_state.fit_completed = False
    st.session_state.fit_warnings = []
    for key in Q_RANGE_WIDGET_KEYS:
        if key in st.session_state:
            del st.session_state[key]


def _clear_model_parameter_state() -> None:
    """Remove widget and update state of the previous model before loading a new one."""
    keys_to_remove = [
        k
        for k in st.session_state.keys()
        if k.startswith(_PARAMETER_WIDGET_PREFIXES) or k in _PARAMETER_STATE_KEYS
    ]
    for key in keys_to_remove:
        del st.session_state[key]


def render_q_range_controls(fitter: SANSFitter) -> None:
    """
    Render the fit Q-range controls (sans-fitter >= 0.4 ``set_q_range``).

    Points outside the range stay visible in the plots but are excluded from
    the fit. Widget keys ``fit_qmin``/``fit_qmax`` are also written by the
    ``set-q-range`` MCP tool so the UI reflects AI-driven changes.

    Args:
        fitter: The SANSFitter instance with loaded data
    """
    q_range = fitter.get_q_range()
    if q_range is None:
        return

    if 'fit_qmin' not in st.session_state:
        st.session_state.fit_qmin = float(q_range[0])
    if 'fit_qmax' not in st.session_state:
        st.session_state.fit_qmax = float(q_range[1])

    st.markdown(Q_RANGE_HEADER)
    range_cols = st.columns(2)
    with range_cols[0]:
        qmin = st.number_input(Q_RANGE_MIN_LABEL, format='%.4g', key='fit_qmin', help=Q_RANGE_HELP)
    with range_cols[1]:
        qmax = st.number_input(Q_RANGE_MAX_LABEL, format='%.4g', key='fit_qmax', help=Q_RANGE_HELP)

    button_cols = st.columns(2)
    with button_cols[0]:
        if st.button(Q_RANGE_APPLY_BUTTON):
            try:
                fitter.set_q_range(qmin=float(qmin), qmax=float(qmax))
                st.success(SUCCESS_Q_RANGE_UPDATED)
            except ValueError as e:
                st.error(f'Invalid Q range: {str(e)}')
    with button_cols[1]:
        if st.button(Q_RANGE_RESET_BUTTON):
            fitter.reset_q_range()
            for key in Q_RANGE_WIDGET_KEYS:
                if key in st.session_state:
                    del st.session_state[key]
            st.success(SUCCESS_Q_RANGE_RESET)
            st.rerun()


def render_resolution_controls(fitter: SANSFitter) -> None:
    """
    Render the resolution (smearing) controls.

    The fitter is the single source of truth. On every run the widgets are set
    from it before they are drawn, and user edits reach it through on_change
    callbacks, so edits made here and changes made elsewhere (an AI tool, a
    loaded analysis) cannot overwrite each other. sans-fitter validates the
    setting; a rejected edit is reported and leaves the fitter unchanged.

    Args:
        fitter: The SANSFitter instance
    """
    current = fitter.get_resolution()
    modes = list(RESOLUTION_MODES)
    st.session_state[RESOLUTION_MODE_KEY] = current['mode'] if current['mode'] in modes else None
    st.session_state[RESOLUTION_DQ_KEY] = current['dq_over_q'] or RESOLUTION_DQ_DEFAULT

    def apply_edit() -> None:
        mode = st.session_state[RESOLUTION_MODE_KEY]
        dq_over_q = st.session_state[RESOLUTION_DQ_KEY] if mode == 'pinhole' else None
        try:
            fitter.set_resolution(mode, dq_over_q=dq_over_q)
        except ValueError as e:
            st.session_state[RESOLUTION_ERROR_KEY] = str(e)

    st.markdown(RESOLUTION_HEADER)
    if current['mode'] not in modes:
        st.caption(RESOLUTION_OTHER_MODE_CAPTION.format(mode=current['mode']))
    st.selectbox(
        RESOLUTION_MODE_LABEL,
        options=modes,
        format_func=RESOLUTION_MODES.get,
        key=RESOLUTION_MODE_KEY,
        on_change=apply_edit,
        help=RESOLUTION_MODE_HELP,
    )
    if st.session_state[RESOLUTION_MODE_KEY] == 'pinhole':
        # No bounds: any width sans-fitter accepts can be shown as it is
        st.number_input(
            RESOLUTION_DQ_LABEL,
            step=0.01,
            format='%g',
            key=RESOLUTION_DQ_KEY,
            on_change=apply_edit,
            help=RESOLUTION_DQ_HELP,
        )

    error = st.session_state.pop(RESOLUTION_ERROR_KEY, None)
    if error:
        st.error(error)


def render_data_upload_sidebar() -> None:
    """Render the data upload controls in the sidebar as a collapsible section."""
    with st.sidebar.expander(
        SIDEBAR_DATA_UPLOAD_HEADER, expanded=st.session_state.expand_data_upload
    ):
        uploaded_file = st.file_uploader(
            UPLOAD_LABEL,
            type=UPLOAD_TYPES,
            help=UPLOAD_HELP,
        )

        if uploaded_file is None:
            st.session_state.last_uploaded_file_id = None

        if st.button(EXAMPLE_DATA_BUTTON):
            example_path = _get_example_data_path()
            if example_path is not None:
                try:
                    st.session_state.fitter.load_data(str(example_path))
                    st.session_state.data_loaded = True
                    _reset_after_data_load()
                    # Collapse data upload, expand model selection
                    st.session_state.expand_data_upload = False
                    st.session_state.expand_model_selection = True
                    st.success(SUCCESS_EXAMPLE_LOADED)
                    st.rerun()
                except Exception as e:
                    st.error(f'Error loading example data: {str(e)}')
            else:
                st.error(ERROR_EXAMPLE_NOT_FOUND)

        if uploaded_file is not None:
            try:
                current_file_id = (uploaded_file.name, uploaded_file.size)
                if st.session_state.last_uploaded_file_id == current_file_id:
                    return

                # Keep the original extension: sasdata picks its reader from it
                # (CanSAS XML and NXcanSAS HDF5 would not load as '.csv').
                suffix = Path(uploaded_file.name).suffix or '.csv'
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name

                try:
                    st.session_state.fitter.load_data(tmp_file_path)
                    st.session_state.data_loaded = True
                    _reset_after_data_load()
                    st.session_state.last_uploaded_file_id = current_file_id
                    # Collapse data upload, expand model selection
                    st.session_state.expand_data_upload = False
                    st.session_state.expand_model_selection = True
                    st.success(SUCCESS_DATA_UPLOADED)
                    st.rerun()
                finally:
                    # Always cleanup temp file, even if exception occurs
                    if os.path.exists(tmp_file_path):
                        os.unlink(tmp_file_path)

            except Exception as e:
                st.error(f'Error loading data: {str(e)}')
                st.session_state.data_loaded = False
                st.session_state.last_uploaded_file_id = None


def render_model_selection_sidebar() -> None:
    """Render the model selection controls in the sidebar as a collapsible section."""
    with st.sidebar.expander(
        SIDEBAR_MODEL_SELECTION_HEADER, expanded=st.session_state.expand_model_selection
    ):
        selection_method = st.radio(
            SELECTION_METHOD_LABEL, SELECTION_METHOD_OPTIONS, help=SELECTION_METHOD_HELP
        )

        selected_model = None

        if selection_method == 'Manual':
            all_models = get_all_models()
            selected_model = st.selectbox(
                MODEL_SELECT_LABEL,
                options=all_models,
                index=all_models.index('sphere') if 'sphere' in all_models else 0,
                help=MODEL_SELECT_HELP,
            )
        else:
            st.markdown(AI_ASSISTED_HEADER)

            api_key = st.text_input(
                AI_KEY_LABEL,
                type='password',
                help=AI_KEY_HELP,
            )

            if api_key:
                st.session_state.chat_api_key = api_key

            if st.button(AI_SUGGESTIONS_BUTTON):
                if st.session_state.data_loaded:
                    with st.spinner(SPINNER_ANALYZING_DATA):
                        data = st.session_state.fitter.data
                        suggestions = suggest_models_ai(
                            data.x, data.y, api_key if api_key else None
                        )

                        if suggestions:
                            st.success(
                                f'{SUCCESS_AI_SUGGESTIONS_PREFIX}{len(suggestions)}{SUCCESS_AI_SUGGESTIONS_SUFFIX}'
                            )
                            st.session_state.ai_suggestions = suggestions
                        else:
                            st.warning(WARNING_NO_SUGGESTIONS)
                else:
                    st.warning(WARNING_LOAD_DATA_FIRST)

            if 'ai_suggestions' in st.session_state and st.session_state.ai_suggestions:
                st.markdown(AI_SUGGESTIONS_HEADER)
                selected_model = st.selectbox(
                    AI_SUGGESTIONS_SELECT_LABEL, options=st.session_state.ai_suggestions
                )

        if selected_model:
            if st.button(LOAD_MODEL_BUTTON):
                try:
                    _clear_model_parameter_state()

                    st.session_state.fitter.set_model(selected_model)
                    st.session_state.model_selected = True
                    st.session_state.current_model = selected_model
                    st.session_state.fit_completed = False
                    # Collapse model selection and data preview (do NOT expand fitting)
                    st.session_state.expand_model_selection = False
                    st.session_state.expand_data_preview = False
                    st.session_state.expand_parameters = True
                    st.success(
                        f'{SUCCESS_MODEL_LOADED_PREFIX}{selected_model}{SUCCESS_MODEL_LOADED_SUFFIX}'
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f'Error loading model: {str(e)}')


def render_ai_chat_sidebar(api_key: Optional[str], fitter: SANSFitter) -> None:
    """
    Render the AI Chat pane as a collapsible section in the left sidebar.
    Uses an expander that is collapsed by default.

    Args:
        api_key: Anthropic API key from the sidebar
        fitter: The SANSFitter instance
    """
    with st.sidebar:
        st.markdown('---')
        with st.expander(AI_CHAT_SIDEBAR_HEADER, expanded=st.session_state.show_ai_chat):
            st.markdown(AI_CHAT_DESCRIPTION)

            # AI Tools Enabled Toggle
            st.markdown('---')
            ai_tools_enabled = st.toggle(
                '🔧 Enable AI Tools',
                value=st.session_state.get('ai_tools_enabled', False),
                help='When enabled, the AI can directly modify model settings, run fits, and update plots.',
                key='ai_tools_toggle',
            )
            st.session_state.ai_tools_enabled = ai_tools_enabled

            if ai_tools_enabled:
                st.caption('✅ AI can modify model parameters and run fits')
            else:
                st.caption('🔒 AI is in read-only mode (chat only)')

            st.markdown('---')

            # Initialize chat history in session state
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []

            # Prompt input area (fixed height text area)
            user_prompt = st.text_area(
                'Your message:',
                height=CHAT_INPUT_HEIGHT,
                placeholder=AI_CHAT_INPUT_PLACEHOLDER,
                key='chat_input',
                label_visibility='collapsed',
            )

            # Send button
            col_send, col_clear = st.columns([1, 1])
            with col_send:
                send_clicked = st.button(
                    AI_CHAT_SEND_BUTTON, type='primary', use_container_width=True
                )
            with col_clear:
                clear_clicked = st.button(AI_CHAT_CLEAR_BUTTON, use_container_width=True)

            # Handle clear
            if clear_clicked:
                st.session_state.chat_history = []
                st.rerun()

            # Handle send
            if send_clicked and user_prompt.strip():
                # Show status while processing
                with st.status(AI_CHAT_THINKING, expanded=True) as status:
                    st.write('Sending message to AI...')

                    response = send_chat_message(user_prompt.strip(), api_key, fitter)

                    # Check if tools were used (response contains tool markers)
                    if '[Used tool:' in response:
                        st.write('🔧 AI used tools to modify settings')

                    st.session_state.chat_history.append(
                        {'role': 'user', 'content': user_prompt.strip()}
                    )
                    st.session_state.chat_history.append({'role': 'assistant', 'content': response})

                    status.update(label='Complete!', state='complete', expanded=False)

                # Check if UI refresh is needed (tools modified state)
                if st.session_state.get('needs_rerun', False):
                    st.session_state.needs_rerun = False

                st.rerun()

            # Display chat history (non-editable but selectable)
            st.markdown('---')
            st.markdown(AI_CHAT_HISTORY_HEADER)

            if st.session_state.chat_history:
                # Create a scrollable container for chat history
                chat_container = st.container(height=CHAT_HISTORY_HEIGHT)
                with chat_container:
                    for _i, message in enumerate(st.session_state.chat_history):
                        if message['role'] == 'user':
                            st.markdown('**🧑 You:**')
                            st.info(message['content'])
                        else:
                            st.markdown('**🤖 Assistant:**')
                            # Check for tool usage in response
                            content = message['content']

                            # If the assistant indicates it used tools, present the main response
                            if '[Used tool:' in content:
                                # Split out tool invocation log
                                parts = content.rsplit('\n\n[Used tool:', 1)
                                main_response = parts[0]
                                st.success(main_response)
                                if len(parts) > 1:
                                    tool_log = '[Used tool:' + parts[1]
                                    st.caption(f'🔧 {tool_log}')
                            else:
                                st.success(content)

                            # If the assistant asked the user to enable AI tools, offer an inline button
                            try:
                                if response_requests_enable_tools(content):
                                    if st.button(
                                        'Enable AI Tools', key=f'enable_ai_tools_msg_{_i}'
                                    ):
                                        st.session_state.ai_tools_enabled = True
                                        st.success(
                                            '✅ AI Tools enabled. Send your message again and I can make the change for you.'
                                        )
                                        st.rerun()
                            except Exception:
                                # If detection or session interaction fails, silently ignore
                                pass
            else:
                st.caption(AI_CHAT_EMPTY_CAPTION)


def render_ai_chat_column(api_key: Optional[str], fitter: SANSFitter) -> None:
    """
    Render the AI Chat in the right column using st.chat_message and st.chat_input.
    Styled like VS Code's chat panel with messages above and input at the bottom.

    Args:
        api_key: Anthropic API key from the sidebar
        fitter: The SANSFitter instance
    """
    st.markdown(AI_CHAT_SIDEBAR_HEADER)
    st.caption(AI_CHAT_DESCRIPTION)

    # AI Tools Enabled Toggle
    ai_tools_enabled = st.toggle(
        '🔧 Enable AI Tools',
        value=st.session_state.get('ai_tools_enabled', False),
        help='When enabled, the AI can directly modify model settings, run fits, and update plots.',
        key='ai_tools_toggle_col',
    )
    st.session_state.ai_tools_enabled = ai_tools_enabled

    if ai_tools_enabled:
        st.caption('✅ AI can modify model parameters and run fits')
    else:
        st.caption('🔒 AI is in read-only mode (chat only)')

    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history using st.chat_message
    chat_container = st.container(height=450)
    with chat_container:
        if st.session_state.chat_history:
            for message in st.session_state.chat_history:
                with st.chat_message(message['role']):
                    st.markdown(message['content'])
        else:
            st.caption(AI_CHAT_EMPTY_CAPTION)

        # Also support enabling AI tools directly from the chat column when the assistant
        # has asked the user to enable AI tools.
        if st.session_state.chat_history:
            # Find last assistant message
            last_assistant = None
            for message in reversed(st.session_state.chat_history):
                if message['role'] == 'assistant':
                    last_assistant = message
                    break

            if last_assistant is not None:
                try:
                    if response_requests_enable_tools(last_assistant['content']):
                        if st.button('Enable AI Tools (from chat)', key='enable_ai_tools_col'):
                            st.session_state.ai_tools_enabled = True
                            st.success(
                                '✅ AI Tools enabled. Send your message again and I can make the change for you.'
                            )
                            st.rerun()
                except Exception:
                    pass

    # Clear button above the input
    if st.session_state.chat_history:
        if st.button(AI_CHAT_CLEAR_BUTTON, key='clear_chat_col'):
            st.session_state.chat_history = []
            st.rerun()

    # Chat input at the bottom using st.chat_input
    if user_prompt := st.chat_input(AI_CHAT_INPUT_PLACEHOLDER, key='chat_input_col'):
        # Add user message to history
        st.session_state.chat_history.append({'role': 'user', 'content': user_prompt})

        # Get AI response
        with st.spinner(AI_CHAT_THINKING):
            response = send_chat_message(user_prompt, api_key, fitter)
            st.session_state.chat_history.append({'role': 'assistant', 'content': response})

        st.rerun()
