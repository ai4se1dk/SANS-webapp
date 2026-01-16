"""
Sidebar components for SANS webapp.

Contains rendering functions for the sidebar sections:
- Data upload
- Model selection
- AI chat
"""

import os
import tempfile
from typing import Optional

import streamlit as st
from sans_fitter import SANSFitter

from sans_analysis_utils import get_all_models
from services.ai_chat import send_chat_message, suggest_models_ai
from ui_constants import (
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


def render_data_upload_sidebar() -> None:
    """Render the data upload controls in the sidebar."""
    st.sidebar.header(SIDEBAR_DATA_UPLOAD_HEADER)

    uploaded_file = st.sidebar.file_uploader(
        UPLOAD_LABEL,
        type=['csv', 'dat'],
        help=UPLOAD_HELP,
    )

    if st.sidebar.button(EXAMPLE_DATA_BUTTON):
        example_file = EXAMPLE_DATA_FILE
        if os.path.exists(example_file):
            try:
                st.session_state.fitter.load_data(example_file)
                st.session_state.data_loaded = True
                st.sidebar.success(SUCCESS_EXAMPLE_LOADED)
            except Exception as e:
                st.sidebar.error(f'Error loading example data: {str(e)}')
        else:
            st.sidebar.error(ERROR_EXAMPLE_NOT_FOUND)

    if uploaded_file is not None:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            st.session_state.fitter.load_data(tmp_file_path)
            st.session_state.data_loaded = True
            st.sidebar.success(SUCCESS_DATA_UPLOADED)

            os.unlink(tmp_file_path)

        except Exception as e:
            st.sidebar.error(f'Error loading data: {str(e)}')
            st.session_state.data_loaded = False


def render_model_selection_sidebar() -> None:
    """Render the model selection controls in the sidebar."""
    st.sidebar.header(SIDEBAR_MODEL_SELECTION_HEADER)

    selection_method = st.sidebar.radio(
        SELECTION_METHOD_LABEL, SELECTION_METHOD_OPTIONS, help=SELECTION_METHOD_HELP
    )

    selected_model = None

    if selection_method == 'Manual':
        all_models = get_all_models()
        selected_model = st.sidebar.selectbox(
            MODEL_SELECT_LABEL,
            options=all_models,
            index=all_models.index('sphere') if 'sphere' in all_models else 0,
            help=MODEL_SELECT_HELP,
        )
    else:
        st.sidebar.markdown(AI_ASSISTED_HEADER)

        api_key = st.sidebar.text_input(
            AI_KEY_LABEL,
            type='password',
            help=AI_KEY_HELP,
        )

        if api_key:
            st.session_state.chat_api_key = api_key

        if st.sidebar.button(AI_SUGGESTIONS_BUTTON):
            if st.session_state.data_loaded:
                with st.spinner(SPINNER_ANALYZING_DATA):
                    data = st.session_state.fitter.data
                    suggestions = suggest_models_ai(data.x, data.y, api_key if api_key else None)

                    if suggestions:
                        st.sidebar.success(
                            f'{SUCCESS_AI_SUGGESTIONS_PREFIX}{len(suggestions)}{SUCCESS_AI_SUGGESTIONS_SUFFIX}'
                        )
                        st.session_state.ai_suggestions = suggestions
                    else:
                        st.sidebar.warning(WARNING_NO_SUGGESTIONS)
            else:
                st.sidebar.warning(WARNING_LOAD_DATA_FIRST)

        if 'ai_suggestions' in st.session_state and st.session_state.ai_suggestions:
            st.sidebar.markdown(AI_SUGGESTIONS_HEADER)
            selected_model = st.sidebar.selectbox(
                AI_SUGGESTIONS_SELECT_LABEL, options=st.session_state.ai_suggestions
            )

    if selected_model:
        if st.sidebar.button(LOAD_MODEL_BUTTON):
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
                st.sidebar.success(
                    f'{SUCCESS_MODEL_LOADED_PREFIX}{selected_model}{SUCCESS_MODEL_LOADED_SUFFIX}'
                )
            except Exception as e:
                st.sidebar.error(f'Error loading model: {str(e)}')


def render_ai_chat_sidebar(api_key: Optional[str], fitter: SANSFitter) -> None:
    """
    Render the AI Chat pane as a collapsible section in the left sidebar.
    Uses an expander that is collapsed by default.

    Args:
        api_key: OpenAI API key from the sidebar
        fitter: The SANSFitter instance
    """
    with st.sidebar:
        st.markdown('---')
        with st.expander(AI_CHAT_SIDEBAR_HEADER, expanded=st.session_state.show_ai_chat):
            st.markdown(AI_CHAT_DESCRIPTION)

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
                with st.spinner(AI_CHAT_THINKING):
                    response = send_chat_message(user_prompt.strip(), api_key, fitter)
                    st.session_state.chat_history.append(
                        {'role': 'user', 'content': user_prompt.strip()}
                    )
                    st.session_state.chat_history.append({'role': 'assistant', 'content': response})
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
                            st.success(message['content'])
            else:
                st.caption(AI_CHAT_EMPTY_CAPTION)
