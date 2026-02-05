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

from sans_webapp.services.ai_chat import send_chat_message, suggest_models_ai, response_requests_enable_tools
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
    UPLOAD_HELP,
    UPLOAD_LABEL,
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


def render_data_upload_sidebar() -> None:
    """Render the data upload controls in the sidebar as a collapsible section."""
    with st.sidebar.expander(
        SIDEBAR_DATA_UPLOAD_HEADER, expanded=st.session_state.expand_data_upload
    ):
        uploaded_file = st.file_uploader(
            UPLOAD_LABEL,
            type=['csv', 'dat'],
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

                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name

                st.session_state.fitter.load_data(tmp_file_path)
                st.session_state.data_loaded = True
                st.session_state.last_uploaded_file_id = current_file_id
                # Collapse data upload, expand model selection
                st.session_state.expand_data_upload = False
                st.session_state.expand_model_selection = True
                st.success(SUCCESS_DATA_UPLOADED)

                os.unlink(tmp_file_path)
                st.rerun()

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
                    keys_to_remove = [
                        k
                        for k in st.session_state.keys()
                        if k.startswith('value_')
                        or k.startswith('min_')
                        or k.startswith('max_')
                        or k.startswith('vary_')
                    ]
                    for key in keys_to_remove:
                        del st.session_state[key]

                    st.session_state.fitter.set_model(selected_model)
                    st.session_state.model_selected = True
                    st.session_state.current_model = selected_model
                    st.session_state.fit_completed = False
                    # Collapse model selection (do NOT expand fitting)
                    st.session_state.expand_model_selection = False
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
                send_clicked = st.button(AI_CHAT_SEND_BUTTON, type='primary', use_container_width=True)
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
                                    if st.button('Enable AI Tools', key=f'enable_ai_tools_msg_{_i}'):
                                        st.session_state.ai_tools_enabled = True
                                        st.success('✅ AI Tools enabled. Send your message again and I can make the change for you.')
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
                            st.success('✅ AI Tools enabled. Send your message again and I can make the change for you.')
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
