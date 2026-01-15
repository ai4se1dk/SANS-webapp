"""
SANS Data Analysis Web Application

A Streamlit-based web application for Small Angle Neutron Scattering (SANS) data analysis.
Features include data upload, model selection (manual and AI-assisted), parameter fitting,
and interactive visualization.
"""

import os
import tempfile
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
from sans_fitter import SANSFitter
from sasmodels.direct_model import DirectModel

from sans_analysis_utils import (
    analyze_data_for_ai_suggestion,
    get_all_models,
    plot_data_and_fit,
    suggest_models_simple,
)

# Maximum value that Streamlit's number_input can handle
MAX_FLOAT_DISPLAY = 1e300
MIN_FLOAT_DISPLAY = -1e300


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
        return "⚠️ No API key provided. Please enter your OpenAI API key in the sidebar under 'AI-Assisted' model selection."

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        # Build context about current state
        context_parts = ["You are a SANS (Small Angle Neutron Scattering) data analysis expert assistant."]

        if fitter.data is not None:
            data = fitter.data
            context_parts.append(f"\nCurrent data loaded: {len(data.x)} data points")
            context_parts.append(f"Q range: {data.x.min():.4f} - {data.x.max():.4f} Å⁻¹")
            context_parts.append(f"Intensity range: {data.y.min():.4e} - {data.y.max():.4e} cm⁻¹")

        # Add current model information
        if 'current_model' in st.session_state and st.session_state.model_selected:
            context_parts.append(f"\nCurrent model: {st.session_state.current_model}")
            
            # Add all parameter details
            if fitter.params:
                context_parts.append("\nModel parameters:")
                for name, info in fitter.params.items():
                    vary_status = "fitted" if info['vary'] else "fixed"
                    context_parts.append(f"  - {name}: value={info['value']:.4g}, min={info['min']:.4g}, max={info['max']:.4g} ({vary_status})")

        # Add fit results if available
        if 'fit_result' in st.session_state and st.session_state.fit_completed:
            fit_result = st.session_state.fit_result
            context_parts.append("\nFit results:")
            if 'chisq' in fit_result:
                context_parts.append(f"  Chi² (goodness of fit): {fit_result['chisq']:.4f}")
            
            # Add fitted parameter values with uncertainties
            if 'parameters' in fit_result:
                context_parts.append("  Fitted parameter values:")
                for name, param_info in fit_result['parameters'].items():
                    if name in fitter.params and fitter.params[name]['vary']:
                        stderr = param_info.get('stderr', 'N/A')
                        if isinstance(stderr, (int, float)):
                            context_parts.append(f"    - {name}: {param_info['value']:.4g} ± {stderr:.4g}")
                        else:
                            context_parts.append(f"    - {name}: {param_info['value']:.4g} ± {stderr}")

        system_message = "\n".join(context_parts)
        system_message += "\n\nHelp the user with their SANS data analysis questions. Be concise and helpful."

        response = client.chat.completions.create(
            model='gpt-4o',
            max_tokens=1000,
            messages=[
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': user_message},
            ],
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Error: {str(e)}"


def render_ai_chat_pane(api_key: Optional[str], fitter):
    """
    Render the AI Chat pane in the right column.

    Args:
        api_key: OpenAI API key from the sidebar
        fitter: The SANSFitter instance
    """
    st.markdown("### 🤖 AI Assistant")
    st.markdown("Ask questions about SANS data analysis, model selection, or parameter interpretation.")

    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Prompt input area (fixed height text area)
    user_prompt = st.text_area(
        "Your message:",
        height=100,
        placeholder="Type your question here... (Press Enter for new line)",
        key="chat_input",
        label_visibility="collapsed",
    )

    # Send button
    col_send, col_clear = st.columns([1, 1])
    with col_send:
        send_clicked = st.button("📤 Send", type="primary", use_container_width=True)
    with col_clear:
        clear_clicked = st.button("🗑️ Clear", use_container_width=True)

    # Handle clear
    if clear_clicked:
        st.session_state.chat_history = []
        st.rerun()

    # Handle send
    if send_clicked and user_prompt.strip():
        with st.spinner("Thinking..."):
            response = send_chat_message(user_prompt.strip(), api_key, fitter)
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_prompt.strip()
            })
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': response
            })
        st.rerun()

    # Display chat history (non-editable but selectable)
    st.markdown("---")
    st.markdown("**Conversation:**")

    if st.session_state.chat_history:
        # Create a scrollable container for chat history
        chat_container = st.container(height=400)
        with chat_container:
            for i, message in enumerate(st.session_state.chat_history):
                if message['role'] == 'user':
                    st.markdown(f"**🧑 You:**")
                    st.info(message['content'])
                else:
                    st.markdown(f"**🤖 Assistant:**")
                    st.success(message['content'])
    else:
        st.caption("No messages yet. Ask a question to get started!")


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
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

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

        response = client.chat.completions.create(
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
        page_title='SANS Data Analysis',
        page_icon='🔬',
        layout='wide',
        initial_sidebar_state='expanded',
    )

    st.title('🔬 SANS Data Analysis Web Application')
    st.markdown(
        """
    Analyze Small Angle Neutron Scattering (SANS) data with model fitting and AI-assisted model selection.
    """
    )

    # Initialize session state
    if 'fitter' not in st.session_state:
        st.session_state.fitter = SANSFitter()
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'model_selected' not in st.session_state:
        st.session_state.model_selected = False
    if 'fit_completed' not in st.session_state:
        st.session_state.fit_completed = False
    if 'show_ai_chat' not in st.session_state:
        st.session_state.show_ai_chat = False
    if 'chat_api_key' not in st.session_state:
        st.session_state.chat_api_key = None
    if 'slider_value' not in st.session_state:
        st.session_state.slider_value = 0.0
    if 'prev_selected_param' not in st.session_state:
        st.session_state.prev_selected_param = None

    # Sidebar for controls
    st.sidebar.header('Controls')

    # AI Chat toggle at the top of sidebar
    st.sidebar.markdown('---')
    if st.sidebar.toggle('🤖 AI Chat', value=st.session_state.show_ai_chat, key='ai_chat_toggle'):
        st.session_state.show_ai_chat = True
    else:
        st.session_state.show_ai_chat = False
    st.sidebar.markdown('---')

    # Data Upload section
    st.sidebar.header('Data Upload')

    # File uploader
    uploaded_file = st.sidebar.file_uploader(
        'Upload SANS data file (CSV or .dat)',
        type=['csv', 'dat'],
        help='File should contain columns: Q, I(Q), dI(Q)',
    )

    # Example data button
    if st.sidebar.button('Load Example Data'):
        example_file = 'simulated_sans_data.csv'
        if os.path.exists(example_file):
            try:
                st.session_state.fitter.load_data(example_file)
                st.session_state.data_loaded = True
                st.sidebar.success('✓ Example data loaded successfully!')
            except Exception as e:
                st.sidebar.error(f'Error loading example data: {str(e)}')
        else:
            st.sidebar.error('Example data file not found!')

    # Process uploaded file
    if uploaded_file is not None:
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            # Load data
            st.session_state.fitter.load_data(tmp_file_path)
            st.session_state.data_loaded = True
            st.sidebar.success('✓ Data uploaded successfully!')

            # Clean up temp file
            os.unlink(tmp_file_path)

        except Exception as e:
            st.sidebar.error(f'Error loading data: {str(e)}')
            st.session_state.data_loaded = False

    # Model Selection (in sidebar)
    st.sidebar.header('Model Selection')

    selection_method = st.sidebar.radio(
        'Selection Method', ['Manual', 'AI-Assisted'], help='Choose how to select the fitting model'
    )

    selected_model = None

    if selection_method == 'Manual':
        all_models = get_all_models()
        selected_model = st.sidebar.selectbox(
            'Select Model',
            options=all_models,
            index=all_models.index('sphere') if 'sphere' in all_models else 0,
            help='Choose a model from the sasmodels library',
        )

    else:  # AI-Assisted
        st.sidebar.markdown('**AI-Assisted Model Suggestion**')

        # API key input (optional)
        api_key = st.sidebar.text_input(
            'OpenAI API Key (optional)',
            type='password',
            help='Enter your OpenAI API key for AI-powered suggestions. Leave empty for heuristic-based suggestions.',
        )

        # Store API key for chat pane
        if api_key:
            st.session_state.chat_api_key = api_key

        if st.sidebar.button('Get AI Suggestions'):
            if st.session_state.data_loaded:
                with st.spinner('Analyzing data...'):
                    data = st.session_state.fitter.data
                    suggestions = suggest_models_ai(data.x, data.y, api_key if api_key else None)

                    if suggestions:
                        st.sidebar.success(f'✓ Found {len(suggestions)} suggestions')
                        st.session_state.ai_suggestions = suggestions
                    else:
                        st.sidebar.warning('No suggestions found')
            else:
                st.sidebar.warning('Please load data first')

        # Show suggestions if available
        if 'ai_suggestions' in st.session_state and st.session_state.ai_suggestions:
            st.sidebar.markdown('**Suggested Models:**')
            selected_model = st.sidebar.selectbox(
                'Choose from suggestions', options=st.session_state.ai_suggestions
            )

    # Load selected model
    if selected_model:
        if st.sidebar.button('Load Model'):
            try:
                # Clear old parameter session state before loading new model
                keys_to_remove = [k for k in st.session_state.keys() 
                                  if k.startswith('value_') or k.startswith('min_') 
                                  or k.startswith('max_') or k.startswith('vary_')]
                for key in keys_to_remove:
                    del st.session_state[key]
                
                st.session_state.fitter.set_model(selected_model)
                st.session_state.model_selected = True
                st.session_state.current_model = selected_model
                st.session_state.fit_completed = False  # Reset fit status
                st.sidebar.success(f'✓ Model "{selected_model}" loaded!')
            except Exception as e:
                st.sidebar.error(f'Error loading model: {str(e)}')

    # Main content area - handle case when data is not loaded
    if not st.session_state.data_loaded:
        if st.session_state.show_ai_chat:
            main_col, chat_col = st.columns([3, 1])
            with chat_col:
                render_ai_chat_pane(st.session_state.chat_api_key, st.session_state.fitter)
            with main_col:
                st.info('👆 Please upload a SANS data file or load example data from the sidebar.')
                st.markdown(
                    """
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
                )
        else:
            st.info('👆 Please upload a SANS data file or load example data from the sidebar.')
            st.markdown(
                """
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
            )
        return

    # Data is loaded - create layout with optional AI Chat pane
    if st.session_state.show_ai_chat:
        main_col, chat_col = st.columns([3, 1])
        with chat_col:
            render_ai_chat_pane(st.session_state.chat_api_key, st.session_state.fitter)
    else:
        main_col = st.container()

    # Main content in the main column
    with main_col:
        # Show data preview
        st.subheader('📊 Data Preview')
        col1, col2 = st.columns([2, 1])

        with col1:
            # Plot data
            fig = plot_data_and_fit(st.session_state.fitter, show_fit=False)
            st.plotly_chart(fig, width='stretch')

        with col2:
            st.markdown('**Data Statistics**')
            data = st.session_state.fitter.data
            st.metric('Data Points', len(data.x))
            st.metric('Q Range', f'{data.x.min():.4f} - {data.x.max():.4f} Å⁻¹')
            st.metric('Max Intensity', f'{data.y.max():.4e} cm⁻¹')

            # Show data table
            if st.checkbox('Show data table'):
                df = pd.DataFrame({'Q': data.x, 'I(Q)': data.y, 'dI(Q)': data.dy})
                st.dataframe(df.head(20), height=300)

        # Parameter Configuration
        if st.session_state.model_selected:
            st.subheader(f'⚙️ Model Parameters: {st.session_state.current_model}')

            fitter = st.session_state.fitter
            params = fitter.params

            # Apply pending preset action before widgets are rendered
            if 'pending_preset' in st.session_state:
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

            # Apply pending fit results update before widgets are rendered
            if 'pending_update_from_fit' in st.session_state:
                del st.session_state.pending_update_from_fit
                # Get fitted values from fit_result if available
                if 'fit_result' in st.session_state and 'parameters' in st.session_state.fit_result:
                    for param_name, fit_param_info in st.session_state.fit_result['parameters'].items():
                        if param_name in params:
                            st.session_state[f'value_{param_name}'] = clamp_for_display(float(fit_param_info['value']))
                            # Also update the fitter
                            fitter.set_param(param_name, value=fit_param_info['value'])
                else:
                    # Fallback to fitter params
                    for param_name, param_info in params.items():
                        st.session_state[f'value_{param_name}'] = clamp_for_display(float(param_info['value']))

            st.markdown(
                """
            Configure the model parameters below. Set initial values, bounds, and whether each parameter
            should be fitted (vary) or held constant.
            """
            )

            # Create parameter configuration UI
            param_cols = st.columns([2, 1, 1, 1, 1])
            param_cols[0].markdown('**Parameter**')
            param_cols[1].markdown('**Value**')
            param_cols[2].markdown('**Min**')
            param_cols[3].markdown('**Max**')
            param_cols[4].markdown('**Fit?**')

            # Store parameter updates
            param_updates = {}

            for param_name, param_info in params.items():
                cols = st.columns([2, 1, 1, 1, 1])

                with cols[0]:
                    st.text(param_name)
                    if param_info.get('description'):
                        st.caption(param_info['description'][:50])

                # Initialize session state from fitter only if not already set
                # Once set, session state is the source of truth
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
                        'Value',
                        format='%g',
                        key=value_key,
                        label_visibility='collapsed',
                    )

                with cols[2]:
                    min_val = st.number_input(
                        'Min',
                        format='%g',
                        key=min_key,
                        label_visibility='collapsed',
                    )

                with cols[3]:
                    max_val = st.number_input(
                        'Max',
                        format='%g',
                        key=max_key,
                        label_visibility='collapsed',
                    )

                with cols[4]:
                    vary = st.checkbox(
                        'Fit',
                        key=vary_key,
                        label_visibility='collapsed',
                    )

                # Always sync session state values to fitter
                fitter.set_param(
                    param_name,
                    value=value,
                    min=min_val,
                    max=max_val,
                    vary=vary
                )

                param_updates[param_name] = {
                    'value': value,
                    'min': min_val,
                    'max': max_val,
                    'vary': vary,
                }

            # Apply parameter updates button (now mainly for confirmation feedback)
            if st.button('Update Parameters'):
                st.success('✓ Parameters updated!')

            # Quick parameter presets
            st.markdown('**Quick Presets:**')
            preset_cols = st.columns(4)

            with preset_cols[0]:
                if st.button('Fit Scale & Background'):
                    st.session_state.pending_preset = 'scale_background'
                    st.rerun()

            with preset_cols[1]:
                if st.button('Fit All Parameters'):
                    st.session_state.pending_preset = 'fit_all'
                    st.rerun()

            with preset_cols[2]:
                if st.button('Fix All Parameters'):
                    st.session_state.pending_preset = 'fix_all'
                    st.rerun()

            # Fitting Section (in sidebar)
            st.sidebar.header('Fitting')

            engine = st.sidebar.selectbox(
                'Optimization Engine', ['bumps', 'lmfit'], help='Choose the fitting engine'
            )

            if engine == 'bumps':
                method = st.sidebar.selectbox(
                    'Method',
                    ['amoeba', 'lm', 'newton', 'de'],
                    help='Optimization method for BUMPS',
                )
            else:
                method = st.sidebar.selectbox(
                    'Method',
                    ['leastsq', 'least_squares', 'differential_evolution'],
                    help='Optimization method for LMFit',
                )

            if st.sidebar.button('🚀 Run Fit', type='primary'):
                # Apply current parameter settings before fitting
                for param_name, updates in param_updates.items():
                    fitter.set_param(
                        param_name,
                        value=updates['value'],
                        min=updates['min'],
                        max=updates['max'],
                        vary=updates['vary'],
                    )

                with st.spinner(f'Fitting with {engine}/{method}...'):
                    try:
                        any_vary = any(p['vary'] for p in fitter.params.values())
                        if not any_vary:
                            st.warning(
                                '⚠️ No parameters are set to vary. Please enable at least one parameter to fit.'
                            )
                        else:
                            result = fitter.fit(engine=engine, method=method)
                            st.session_state.fit_completed = True
                            st.session_state.fit_result = result
                            st.sidebar.success('✓ Fit completed successfully!')
                    except Exception as e:
                        st.sidebar.error(f'Fitting error: {str(e)}')

            # Display fit results
            if st.session_state.fit_completed:
                st.subheader('📈 Fit Results')

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
                        chi_squared = st.session_state.fit_result['chisq']
                        st.markdown(f'**Chi² (χ²):** {chi_squared:.4f}')
                        st.markdown('---')

                    st.markdown('**Fitted Parameters**')

                    fitted_params = []
                    if 'fit_result' in st.session_state and 'parameters' in st.session_state.fit_result:
                        for name, param_info in st.session_state.fit_result['parameters'].items():
                            if name in fitter.params and fitter.params[name]['vary']:
                                fitted_params.append({
                                    'Parameter': name,
                                    'Value': f'{param_info["value"]:.4g}',
                                    'Error': f'{param_info["stderr"]:.4g}'
                                })
                    else:
                        for name, info in fitter.params.items():
                            if info['vary']:
                                fitted_params.append({
                                    'Parameter': name,
                                    'Value': f'{info["value"]:.4g}',
                                    'Error': 'N/A'
                                })

                    if fitted_params:
                        df_fitted = pd.DataFrame(fitted_params)
                        st.dataframe(df_fitted, hide_index=True, width='stretch')

                        st.markdown('**Adjust Parameter**')
                        fitted_param_names = [p['Parameter'] for p in fitted_params]

                        selected_param = st.selectbox(
                            'Select parameter to adjust',
                            options=fitted_param_names,
                            key='selected_slider_param',
                            label_visibility='collapsed'
                        )

                        if selected_param:
                            current_value = fitter.params[selected_param]['value']

                            if 'prev_selected_param' not in st.session_state or st.session_state.prev_selected_param != selected_param:
                                st.session_state.slider_value = current_value
                                st.session_state.prev_selected_param = selected_param

                            if current_value != 0:
                                slider_min = current_value * 0.8
                                slider_max = current_value * 1.2
                            else:
                                slider_min = -0.1
                                slider_max = 0.1

                            def update_profile():
                                new_value = st.session_state.slider_value
                                fitter.set_param(selected_param, value=new_value)
                                if f'value_{selected_param}' in st.session_state:
                                    st.session_state[f'value_{selected_param}'] = new_value

                            slider_value = st.slider(
                                f'{selected_param}',
                                min_value=float(slider_min),
                                max_value=float(slider_max),
                                value=float(st.session_state.slider_value),
                                format='%.4g',
                                key='slider_value',
                                on_change=update_profile,
                                label_visibility='collapsed'
                            )

                            st.caption(f'Range: {slider_min:.4g} to {slider_max:.4g}')

                        if st.button('Update Parameters with Fit Results'):
                            st.session_state.pending_update_from_fit = True
                            st.rerun()
                    else:
                        st.info('No parameters were fitted')

                    st.markdown('**Export Results**')
                    if st.button('Save Results to CSV'):
                        try:
                            results_data = []
                            for name, info in fitter.params.items():
                                results_data.append({
                                    'Parameter': name,
                                    'Value': info['value'],
                                    'Min': info['min'],
                                    'Max': info['max'],
                                    'Fitted': info['vary'],
                                })

                            df_results = pd.DataFrame(results_data)
                            csv = df_results.to_csv(index=False)

                            st.download_button(
                                label='Download CSV',
                                data=csv,
                                file_name='fit_results.csv',
                                mime='text/csv',
                            )
                        except Exception as e:
                            st.error(f'Error saving results: {str(e)}')


if __name__ == '__main__':
    main()
