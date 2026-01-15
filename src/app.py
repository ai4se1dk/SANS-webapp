"""
SANS Data Analysis Web Application

A Streamlit-based web application for Small Angle Neutron Scattering (SANS) data analysis.
Features include data upload, model selection (manual and AI-assisted), parameter fitting,
and interactive visualization.
"""

import os
import tempfile
from typing import Optional, TypedDict, cast

import numpy as np
import pandas as pd
import streamlit as st
from sans_fitter import SANSFitter
from sasmodels.direct_model import DirectModel

from openai_client import create_chat_completion
from sans_analysis_utils import (
    analyze_data_for_ai_suggestion,
    get_all_models,
    plot_data_and_fit,
    suggest_models_simple,
)

# Maximum value that Streamlit's number_input can handle
MAX_FLOAT_DISPLAY = 1e300
MIN_FLOAT_DISPLAY = -1e300


class ParamInfo(TypedDict):
    value: float
    min: float
    max: float
    vary: bool
    description: str | None


class FitParamInfo(TypedDict, total=False):
    value: float
    stderr: float | str


class FitResult(TypedDict, total=False):
    chisq: float
    parameters: dict[str, FitParamInfo]


class ParamUpdate(TypedDict):
    value: float
    min: float
    max: float
    vary: bool


def init_session_state() -> None:
    """Initialize Streamlit session state with defaults."""
    defaults: dict[str, object] = {
        'fitter': SANSFitter,
        'data_loaded': False,
        'model_selected': False,
        'fit_completed': False,
        'show_ai_chat': False,
        'chat_api_key': None,
        'slider_value': 0.0,
        'prev_selected_param': None,
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default() if callable(default) else default


def apply_pending_preset(fitter: SANSFitter, params: dict[str, ParamInfo]) -> None:
    """Apply pending preset actions before rendering parameter widgets."""
    if 'pending_preset' not in st.session_state:
        return

    preset = st.session_state.pending_preset
    del st.session_state.pending_preset

    for param_name in params.keys():
        if preset == 'scale_background':
            vary = param_name in ('scale', 'background')
        elif preset == 'fit_all':
            vary = True
        elif preset == 'fix_all':
            vary = False
        else:
            vary = False
        fitter.set_param(param_name, vary=vary)
        st.session_state[f'vary_{param_name}'] = vary


def apply_fit_results_to_params(fitter: SANSFitter, params: dict[str, ParamInfo]) -> None:
    """Apply pending fit results to session state and fitter parameters."""
    if 'pending_update_from_fit' not in st.session_state:
        return

    del st.session_state.pending_update_from_fit

    if 'fit_result' in st.session_state and 'parameters' in st.session_state.fit_result:
        fit_result = cast(FitResult, st.session_state.fit_result)
        fit_params = fit_result.get('parameters', {})
        for param_name, fit_param_info in fit_params.items():
            if param_name in params:
                fitted_value = fit_param_info.get('value')
                if fitted_value is None:
                    continue
                st.session_state[f'value_{param_name}'] = clamp_for_display(float(fitted_value))
                fitter.set_param(param_name, value=fitted_value)
        return

    for param_name, param_info in params.items():
        st.session_state[f'value_{param_name}'] = clamp_for_display(float(param_info['value']))


def build_param_updates_from_params(params: dict[str, ParamInfo]) -> dict[str, ParamUpdate]:
    """Build parameter updates from current fitter params."""
    return {
        name: {
            'value': info['value'],
            'min': info['min'],
            'max': info['max'],
            'vary': info['vary'],
        }
        for name, info in params.items()
    }


def apply_param_updates(fitter: SANSFitter, param_updates: dict[str, ParamUpdate]) -> None:
    """Apply parameter updates to the fitter."""
    for param_name, updates in param_updates.items():
        fitter.set_param(
            param_name,
            value=updates['value'],
            min=updates['min'],
            max=updates['max'],
            vary=updates['vary'],
        )


def render_parameter_table(params: dict[str, ParamInfo]) -> dict[str, ParamUpdate]:
    """Render the parameter table and return updates to apply."""
    param_cols = st.columns([2, 1, 1, 1, 1])
    param_cols[0].markdown(PARAMETER_COLUMNS_LABELS[0])
    param_cols[1].markdown(PARAMETER_COLUMNS_LABELS[1])
    param_cols[2].markdown(PARAMETER_COLUMNS_LABELS[2])
    param_cols[3].markdown(PARAMETER_COLUMNS_LABELS[3])
    param_cols[4].markdown(PARAMETER_COLUMNS_LABELS[4])

    param_updates: dict[str, ParamUpdate] = {}

    for param_name, param_info in params.items():
        cols = st.columns([2, 1, 1, 1, 1])

        with cols[0]:
            st.text(param_name)
            description = param_info.get('description')
            if description:
                st.caption(description[:50])

        value_key = f'value_{param_name}'
        min_key = f'min_{param_name}'
        max_key = f'max_{param_name}'
        vary_key = f'vary_{param_name}'

        if value_key not in st.session_state:
            st.session_state[value_key] = clamp_for_display(float(param_info['value']))
        if min_key not in st.session_state:
            st.session_state[min_key] = clamp_for_display(float(param_info['min']))
        if max_key not in st.session_state:
            st.session_state[max_key] = clamp_for_display(float(param_info['max']))
        if vary_key not in st.session_state:
            st.session_state[vary_key] = param_info['vary']

        with cols[1]:
            value = st.number_input(
                PARAMETER_VALUE_LABEL,
                format='%g',
                key=value_key,
                label_visibility='collapsed',
            )

        with cols[2]:
            min_val = st.number_input(
                PARAMETER_MIN_LABEL,
                format='%g',
                key=min_key,
                label_visibility='collapsed',
            )

        with cols[3]:
            max_val = st.number_input(
                PARAMETER_MAX_LABEL,
                format='%g',
                key=max_key,
                label_visibility='collapsed',
            )

        with cols[4]:
            vary = st.checkbox(
                PARAMETER_FIT_LABEL,
                key=vary_key,
                label_visibility='collapsed',
            )

        param_updates[param_name] = {
            'value': value,
            'min': min_val,
            'max': max_val,
            'vary': vary,
        }

    return param_updates

# UI constants
APP_PAGE_TITLE = 'SANS Data Analysis'
APP_PAGE_ICON = '🔬'
APP_LAYOUT = 'wide'
APP_SIDEBAR_STATE = 'expanded'
APP_TITLE = '🔬 SANS Data Analysis Web Application'
APP_SUBTITLE = (
    'Analyze Small Angle Neutron Scattering (SANS) data with model fitting and '
    'AI-assisted model selection.'
)

SIDEBAR_CONTROLS_HEADER = 'Controls'
SIDEBAR_DATA_UPLOAD_HEADER = 'Data Upload'
SIDEBAR_MODEL_SELECTION_HEADER = 'Model Selection'
SIDEBAR_FITTING_HEADER = 'Fitting'

UPLOAD_LABEL = 'Upload SANS data file (CSV or .dat)'
UPLOAD_HELP = 'File should contain columns: Q, I(Q), dI(Q)'
EXAMPLE_DATA_BUTTON = 'Load Example Data'
EXAMPLE_DATA_FILE = 'simulated_sans_data.csv'

SELECTION_METHOD_LABEL = 'Selection Method'
SELECTION_METHOD_OPTIONS = ['Manual', 'AI-Assisted']
SELECTION_METHOD_HELP = 'Choose how to select the fitting model'
MODEL_SELECT_LABEL = 'Select Model'
MODEL_SELECT_HELP = 'Choose a model from the sasmodels library'
AI_ASSISTED_HEADER = '**AI-Assisted Model Suggestion**'
AI_KEY_LABEL = 'OpenAI API Key (optional)'
AI_KEY_HELP = (
    'Enter your OpenAI API key for AI-powered suggestions. '
    'Leave empty for heuristic-based suggestions.'
)
AI_SUGGESTIONS_BUTTON = 'Get AI Suggestions'
AI_SUGGESTIONS_HEADER = '**Suggested Models:**'
AI_SUGGESTIONS_SELECT_LABEL = 'Choose from suggestions'
LOAD_MODEL_BUTTON = 'Load Model'

DATA_PREVIEW_HEADER = '📊 Data Preview'
DATA_STATS_HEADER = '**Data Statistics**'
SHOW_DATA_TABLE_LABEL = 'Show data table'
DATA_TABLE_HEIGHT = 300
METRIC_DATA_POINTS = 'Data Points'
METRIC_Q_RANGE = 'Q Range'
METRIC_MAX_INTENSITY = 'Max Intensity'
DATA_FORMAT_HELP = """
### Expected Data Format

Your data file should be a CSV or .dat file with three columns:
- **Q**: Scattering vector (Å⁻¹)
- **I(Q)**: Intensity (cm⁻¹)
- **dI(Q)**: Error/uncertainty in intensity

Example:
```
Q,I,dI
0.001,1.035,0.020
0.006,0.990,0.020
0.011,1.038,0.020
...
```
"""

PARAMETERS_HEADER_PREFIX = '⚙️ Model Parameters: '
PARAMETERS_HELP_TEXT = (
    'Configure the model parameters below. Set initial values, bounds, and whether each '
    'parameter\nshould be fitted (vary) or held constant.'
)
PARAMETER_COLUMNS_LABELS = ('**Parameter**', '**Value**', '**Min**', '**Max**', '**Fit?**')
PARAMETER_UPDATE_BUTTON = 'Update Parameters'
PARAMETER_VALUE_LABEL = 'Value'
PARAMETER_MIN_LABEL = 'Min'
PARAMETER_MAX_LABEL = 'Max'
PARAMETER_FIT_LABEL = 'Fit'
PRESET_HEADER = '**Quick Presets:**'
PRESET_FIT_SCALE_BACKGROUND = 'Fit Scale & Background'
PRESET_FIT_ALL = 'Fit All Parameters'
PRESET_FIX_ALL = 'Fix All Parameters'

FIT_ENGINE_LABEL = 'Optimization Engine'
FIT_ENGINE_OPTIONS = ['bumps', 'lmfit']
FIT_ENGINE_HELP = 'Choose the fitting engine'
FIT_METHOD_LABEL = 'Method'
FIT_METHOD_BUMPS = ['amoeba', 'lm', 'newton', 'de']
FIT_METHOD_LMFIT = ['leastsq', 'least_squares', 'differential_evolution']
FIT_METHOD_HELP_BUMPS = 'Optimization method for BUMPS'
FIT_METHOD_HELP_LMFIT = 'Optimization method for LMFit'
FIT_RUN_BUTTON = '🚀 Run Fit'

FIT_RESULTS_HEADER = '📈 Fit Results'
CHI_SQUARED_LABEL = '**Chi² (χ²):** '
FITTED_PARAMETERS_HEADER = '**Fitted Parameters**'
ADJUST_PARAMETER_HEADER = '**Adjust Parameter**'
SELECT_PARAMETER_LABEL = 'Select parameter to adjust'
UPDATE_FROM_FIT_BUTTON = 'Update Parameters with Fit Results'
EXPORT_RESULTS_HEADER = '**Export Results**'
SAVE_RESULTS_BUTTON = 'Save Results to CSV'
DOWNLOAD_RESULTS_LABEL = 'Download CSV'
RESULTS_CSV_NAME = 'fit_results.csv'

AI_CHAT_SIDEBAR_HEADER = '🤖 AI Assistant'
AI_CHAT_DESCRIPTION = (
    'Ask questions about SANS data analysis, model selection, or parameter interpretation.'
)
AI_CHAT_INPUT_LABEL = 'Your message:'
AI_CHAT_INPUT_PLACEHOLDER = 'Type your question here... (Press Enter for new line)'
AI_CHAT_SEND_BUTTON = '📤 Send'
AI_CHAT_CLEAR_BUTTON = '🗑️ Clear'
AI_CHAT_HISTORY_HEADER = '**Conversation:**'
AI_CHAT_EMPTY_CAPTION = 'No messages yet. Ask a question to get started!'
AI_CHAT_THINKING = 'Thinking...'

SPINNER_ANALYZING_DATA = 'Analyzing data...'
WARNING_NO_SUGGESTIONS = 'No suggestions found'
WARNING_LOAD_DATA_FIRST = 'Please load data first'
ERROR_EXAMPLE_NOT_FOUND = 'Example data file not found!'

INFO_NO_DATA = '👆 Please upload a SANS data file or load example data from the sidebar.'
WARNING_NO_API_KEY = (
    "⚠️ No API key provided. Please enter your OpenAI API key in the sidebar under "
    "'AI-Assisted' model selection."
)
WARNING_NO_VARY = (
    '⚠️ No parameters are set to vary. Please enable at least one parameter to fit.'
)
SUCCESS_DATA_UPLOADED = '✓ Data uploaded successfully!'
SUCCESS_EXAMPLE_LOADED = '✓ Example data loaded successfully!'
SUCCESS_MODEL_LOADED_PREFIX = '✓ Model "'
SUCCESS_MODEL_LOADED_SUFFIX = '" loaded!'
SUCCESS_FIT_COMPLETED = '✓ Fit completed successfully!'
SUCCESS_PARAMS_UPDATED = '✓ Parameters updated!'
SUCCESS_AI_SUGGESTIONS_PREFIX = '✓ Found '
SUCCESS_AI_SUGGESTIONS_SUFFIX = ' suggestions'

CHAT_INPUT_HEIGHT = 100
CHAT_HISTORY_HEIGHT = 300
RIGHT_SIDEBAR_TOP = 60
RIGHT_SIDEBAR_WIDTH = 350
RIGHT_SIDEBAR_PADDING_RIGHT = 370
SLIDER_SCALE_MIN = 0.8
SLIDER_SCALE_MAX = 1.2
SLIDER_DEFAULT_MIN = -0.1
SLIDER_DEFAULT_MAX = 0.1


def send_chat_message(user_message: str, api_key: Optional[str], fitter) -> str:
    """
    Send a chat message to the OpenAI API for SANS data analysis assistance.

    Args:
        user_message: The user's prompt
        api_key: OpenAI API key
        fitter: The SANSFitter instance with current data/model context

    Returns:
        The AI response text
    """
    if not api_key:
        return WARNING_NO_API_KEY

    try:
        # Build context about current state
        context_parts = [
            'You are a SANS (Small Angle Neutron Scattering) data analysis expert assistant.'
        ]

        if fitter.data is not None:
            data = fitter.data
            context_parts.append(f'\nCurrent data loaded: {len(data.x)} data points')
            context_parts.append(f'Q range: {data.x.min():.4f} - {data.x.max():.4f} Å⁻¹')
            context_parts.append(f'Intensity range: {data.y.min():.4e} - {data.y.max():.4e} cm⁻¹')

        # Add current model information
        if 'current_model' in st.session_state and st.session_state.model_selected:
            context_parts.append(f'\nCurrent model: {st.session_state.current_model}')

            # Add all parameter details
            if fitter.params:
                params = cast(dict[str, ParamInfo], fitter.params)
                context_parts.append('\nModel parameters:')
                for name, info in params.items():
                    vary_status = 'fitted' if info['vary'] else 'fixed'
                    context_parts.append(
                        f'  - {name}: value={info["value"]:.4g}, min={info["min"]:.4g}, max={info["max"]:.4g} ({vary_status})'
                    )

        # Add fit results if available
        if 'fit_result' in st.session_state and st.session_state.fit_completed:
            fit_result = cast(FitResult, st.session_state.fit_result)
            context_parts.append('\nFit results:')
            chisq = fit_result.get('chisq')
            if chisq is not None:
                context_parts.append(f'  Chi² (goodness of fit): {chisq:.4f}')

            # Add fitted parameter values with uncertainties
            if 'parameters' in fit_result:
                context_parts.append('  Fitted parameter values:')
                for name, param_info in fit_result['parameters'].items():
                    if name in fitter.params and fitter.params[name]['vary']:
                        stderr = param_info.get('stderr', 'N/A')
                        value = param_info.get('value')
                        if value is None:
                            continue
                        if isinstance(stderr, (int, float)):
                            context_parts.append(
                                f'    - {name}: {value:.4g} ± {stderr:.4g}'
                            )
                        else:
                            context_parts.append(
                                f'    - {name}: {value:.4g} ± {stderr}'
                            )

        system_message = '\n'.join(context_parts)
        system_message += (
            '\n\nHelp the user with their SANS data analysis questions. Be concise and helpful.'
        )

        response = create_chat_completion(
            api_key=api_key,
            model='gpt-4o',
            max_tokens=1000,
            messages=[
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': user_message},
            ],
        )

        return response.choices[0].message.content

    except Exception as e:
        return f'❌ Error: {str(e)}'


def inject_right_sidebar_css():
    """Inject CSS for the right sidebar."""
    st.markdown(
        f"""
        <style>
        /* Right sidebar container */
        .right-sidebar {{
            position: fixed;
            top: {RIGHT_SIDEBAR_TOP}px;
            right: 0;
            width: {RIGHT_SIDEBAR_WIDTH}px;
            height: calc(100vh - {RIGHT_SIDEBAR_TOP}px);
            background-color: #f8f9fa;
            border-left: 1px solid #ddd;
            padding: 1rem;
            overflow-y: auto;
            z-index: 999;
            transition: transform 0.3s ease-in-out;
        }}

        /* Dark mode support */
        @media (prefers-color-scheme: dark) {{
            .right-sidebar {{
                background-color: #262730;
                border-left: 1px solid #4a4a5a;
            }}
        }}

        /* Streamlit dark mode class */
        [data-testid="stAppViewContainer"][data-theme="dark"] .right-sidebar {{
            background-color: #262730;
            border-left: 1px solid #4a4a5a;
        }}

        /* When right sidebar is open, adjust main content */
        .main-with-right-sidebar .main .block-container {{
            padding-right: {RIGHT_SIDEBAR_PADDING_RIGHT}px !important;
        }}
        </style>
    """,
        unsafe_allow_html=True,
    )


def render_ai_chat_sidebar(api_key: Optional[str], fitter):
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
                AI_CHAT_INPUT_LABEL,
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


def clamp_for_display(value: float) -> float:
    """
    Clamp a value to a range that Streamlit's number_input can handle.
    Converts inf/-inf to displayable bounds.

    Args:
        value: The value to clamp

    Returns:
        The clamped value
    """
    if np.isinf(value):
        return MAX_FLOAT_DISPLAY if value > 0 else MIN_FLOAT_DISPLAY
    return value


def suggest_models_ai(
    q_data: np.ndarray, i_data: np.ndarray, api_key: Optional[str] = None
) -> list[str]:
    """
    AI-powered model suggestion using OpenAI API.

    Args:
        q_data: Q values
        i_data: Intensity values
        api_key: OpenAI API key

    Returns:
        List of suggested model names
    """
    if not api_key:
        st.warning('No API key provided. Using simple heuristic suggestion instead.')
        return suggest_models_simple(q_data, i_data)

    try:
        # Get all available models
        all_models = get_all_models()

        # Create data description
        data_description = analyze_data_for_ai_suggestion(q_data, i_data)

        prompt = f"""You are a SANS (Small Angle Neutron Scattering) data analysis expert.
Analyze the following SANS data and suggest 3 most appropriate models
from the sasmodels library.

The data:
Q (Å⁻¹), I(Q) (cm⁻¹)

{chr(10).join([f'{q_data[i]:.6f}, {i_data[i]:.6f}' for i in range(len(q_data))])}

Data description:

{data_description}

Available models include all models in the sasmodels library.

Based on the data characteristics (slope, Q range, intensity decay), suggest 3 models
that would fit the provided data. Return ONLY the model names, one per line, no explanations."""

        response = create_chat_completion(
            api_key=api_key,
            model='gpt-4o',
            max_tokens=500,
            messages=[{'role': 'user', 'content': prompt}],
        )

        # Parse response
        suggestions = []
        response_text = response.choices[0].message.content
        for line in response_text.strip().split('\n'):
            model_name = line.strip().lower()
            # Remove numbering, bullets, etc.
            model_name = model_name.lstrip('0123456789.-• ')
            if model_name in all_models:
                suggestions.append(model_name)

        return suggestions if suggestions else suggest_models_simple(q_data, i_data)

    except Exception as e:
        st.warning(f'AI suggestion failed: {str(e)}. Using simple heuristic instead.')
        return suggest_models_simple(q_data, i_data)


def main():
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
        # Render AI Chat in left sidebar (at the bottom)
        render_ai_chat_sidebar(st.session_state.chat_api_key, st.session_state.fitter)
        return

    # Data is loaded - main content area
    # Show data preview
    st.subheader(DATA_PREVIEW_HEADER)
    col1, col2 = st.columns([2, 1])

    with col1:
        # Plot data
        fig = plot_data_and_fit(st.session_state.fitter, show_fit=False)
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown(DATA_STATS_HEADER)
        data = st.session_state.fitter.data
        st.metric(METRIC_DATA_POINTS, len(data.x))
        st.metric(METRIC_Q_RANGE, f'{data.x.min():.4f} - {data.x.max():.4f} Å⁻¹')
        st.metric(METRIC_MAX_INTENSITY, f'{data.y.max():.4e} cm⁻¹')

        # Show data table
        if st.checkbox(SHOW_DATA_TABLE_LABEL):
            df = pd.DataFrame({'Q': data.x, 'I(Q)': data.y, 'dI(Q)': data.dy})
            st.dataframe(df.head(20), height=DATA_TABLE_HEIGHT)

    # Parameter Configuration
    if st.session_state.model_selected:
        st.subheader(f'{PARAMETERS_HEADER_PREFIX}{st.session_state.current_model}')

        fitter = st.session_state.fitter
        params = cast(dict[str, ParamInfo], fitter.params)

        # Apply pending updates before widgets are rendered
        apply_pending_preset(fitter, params)
        apply_fit_results_to_params(fitter, params)

        st.markdown(PARAMETERS_HELP_TEXT)

        with st.form('parameter_form'):
            # Create parameter configuration UI
            param_updates = render_parameter_table(params)
            submitted = st.form_submit_button(PARAMETER_UPDATE_BUTTON)

        if submitted:
            apply_param_updates(fitter, param_updates)
            st.session_state.param_updates = param_updates
            st.success(SUCCESS_PARAMS_UPDATED)

        if 'param_updates' not in st.session_state:
            st.session_state.param_updates = build_param_updates_from_params(params)

        param_updates = cast(dict[str, ParamUpdate], st.session_state.param_updates)

        # Quick parameter presets
        st.markdown(PRESET_HEADER)
        preset_cols = st.columns(4)

        with preset_cols[0]:
            if st.button(PRESET_FIT_SCALE_BACKGROUND):
                st.session_state.pending_preset = 'scale_background'
                st.rerun()

        with preset_cols[1]:
            if st.button(PRESET_FIT_ALL):
                st.session_state.pending_preset = 'fit_all'
                st.rerun()

        with preset_cols[2]:
            if st.button(PRESET_FIX_ALL):
                st.session_state.pending_preset = 'fix_all'
                st.rerun()

        # Fitting Section (in sidebar)
        st.sidebar.header(SIDEBAR_FITTING_HEADER)

        engine = st.sidebar.selectbox(FIT_ENGINE_LABEL, FIT_ENGINE_OPTIONS, help=FIT_ENGINE_HELP)

        if engine == 'bumps':
            method = st.sidebar.selectbox(
                FIT_METHOD_LABEL, FIT_METHOD_BUMPS, help=FIT_METHOD_HELP_BUMPS
            )
        else:
            method = st.sidebar.selectbox(
                FIT_METHOD_LABEL, FIT_METHOD_LMFIT, help=FIT_METHOD_HELP_LMFIT
            )

        if st.sidebar.button(FIT_RUN_BUTTON, type='primary'):
            # Apply current parameter settings before fitting
            apply_param_updates(fitter, param_updates)

            with st.spinner(f'Fitting with {engine}/{method}...'):
                try:
                    any_vary = any(p['vary'] for p in fitter.params.values())
                    if not any_vary:
                        st.warning(WARNING_NO_VARY)
                    else:
                        result = fitter.fit(engine=engine, method=method)
                        st.session_state.fit_completed = True
                        st.session_state.fit_result = cast(FitResult, result)
                        st.sidebar.success(SUCCESS_FIT_COMPLETED)
                except Exception as e:
                    st.sidebar.error(f'Fitting error: {str(e)}')

        # Display fit results
        if st.session_state.fit_completed:
            st.subheader(FIT_RESULTS_HEADER)

            col1, col2 = st.columns([2, 1])

            with col1:
                try:
                    param_values = {name: info['value'] for name, info in fitter.params.items()}
                    calculator = DirectModel(fitter.data, fitter.kernel)
                    fit_i = calculator(**param_values)
                    q_plot = fitter.data.x

                    fig = plot_data_and_fit(fitter, show_fit=True, fit_q=q_plot, fit_i=fit_i)
                    st.plotly_chart(fig, width='stretch')

                except Exception as e:
                    st.error(f'Error plotting results: {str(e)}')

            with col2:
                if 'fit_result' in st.session_state and 'chisq' in st.session_state.fit_result:
                    chi_squared = cast(FitResult, st.session_state.fit_result).get('chisq')
                    if chi_squared is not None:
                        st.markdown(f'{CHI_SQUARED_LABEL}{chi_squared:.4f}')
                        st.markdown('---')

                st.markdown(FITTED_PARAMETERS_HEADER)

                fitted_params = []
                if 'fit_result' in st.session_state and 'parameters' in st.session_state.fit_result:
                    fit_result = cast(FitResult, st.session_state.fit_result)
                    for name, param_info in fit_result.get('parameters', {}).items():
                        if name in fitter.params and fitter.params[name]['vary']:
                            value = param_info.get('value')
                            stderr = param_info.get('stderr')
                            if value is None:
                                continue
                            if isinstance(stderr, (int, float)):
                                error_text = f'{stderr:.4g}'
                            elif stderr is None:
                                error_text = 'N/A'
                            else:
                                error_text = f'{stderr}'
                            fitted_params.append(
                                {
                                    'Parameter': name,
                                    'Value': f'{value:.4g}',
                                    'Error': error_text,
                                }
                            )
                else:
                    for name, info in fitter.params.items():
                        if info['vary']:
                            fitted_params.append(
                                {'Parameter': name, 'Value': f'{info["value"]:.4g}', 'Error': 'N/A'}
                            )

                if fitted_params:
                    df_fitted = pd.DataFrame(fitted_params)
                    st.dataframe(df_fitted, hide_index=True, width='stretch')

                    st.markdown(ADJUST_PARAMETER_HEADER)
                    fitted_param_names = [p['Parameter'] for p in fitted_params]

                    selected_param = st.selectbox(
                        SELECT_PARAMETER_LABEL,
                        options=fitted_param_names,
                        key='selected_slider_param',
                        label_visibility='collapsed',
                    )

                    if selected_param:
                        current_value = fitter.params[selected_param]['value']

                        if (
                            'prev_selected_param' not in st.session_state
                            or st.session_state.prev_selected_param != selected_param
                        ):
                            st.session_state.slider_value = current_value
                            st.session_state.prev_selected_param = selected_param

                        if current_value != 0:
                            slider_min = current_value * SLIDER_SCALE_MIN
                            slider_max = current_value * SLIDER_SCALE_MAX
                        else:
                            slider_min = SLIDER_DEFAULT_MIN
                            slider_max = SLIDER_DEFAULT_MAX

                        def update_profile():
                            new_value = st.session_state.slider_value
                            fitter.set_param(selected_param, value=new_value)
                            if f'value_{selected_param}' in st.session_state:
                                st.session_state[f'value_{selected_param}'] = new_value

                        st.slider(
                            f'{selected_param}',
                            min_value=float(slider_min),
                            max_value=float(slider_max),
                            value=float(st.session_state.slider_value),
                            format='%.4g',
                            key='slider_value',
                            on_change=update_profile,
                            label_visibility='collapsed',
                        )

                        st.caption(f'Range: {slider_min:.4g} to {slider_max:.4g}')

                    if st.button(UPDATE_FROM_FIT_BUTTON):
                        st.session_state.pending_update_from_fit = True
                        st.rerun()
                else:
                    st.info('No parameters were fitted')

                st.markdown(EXPORT_RESULTS_HEADER)
                if st.button(SAVE_RESULTS_BUTTON):
                    try:
                        results_data = []
                        for name, info in fitter.params.items():
                            results_data.append(
                                {
                                    'Parameter': name,
                                    'Value': info['value'],
                                    'Min': info['min'],
                                    'Max': info['max'],
                                    'Fitted': info['vary'],
                                }
                            )

                        df_results = pd.DataFrame(results_data)
                        csv = df_results.to_csv(index=False)

                        st.download_button(
                            label=DOWNLOAD_RESULTS_LABEL,
                            data=csv,
                            file_name=RESULTS_CSV_NAME,
                            mime='text/csv',
                        )
                    except Exception as e:
                        st.error(f'Error saving results: {str(e)}')

    # Render AI Chat in left sidebar (at the bottom)
    render_ai_chat_sidebar(st.session_state.chat_api_key, st.session_state.fitter)


if __name__ == '__main__':
    main()
