"""
AI Chat service for SANS webapp.

Contains functions for AI-powered model suggestion and chat functionality.
"""

from typing import Optional, cast

import numpy as np
import streamlit as st
from sans_fitter import SANSFitter

from openai_client import create_chat_completion
from sans_analysis_utils import (
    analyze_data_for_ai_suggestion,
    get_all_models,
    suggest_models_simple,
)
from sans_types import FitResult, ParamInfo
from ui_constants import WARNING_NO_API_KEY


def send_chat_message(user_message: str, api_key: Optional[str], fitter: SANSFitter) -> str:
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
                            context_parts.append(f'    - {name}: {value:.4g} ± {stderr:.4g}')
                        else:
                            context_parts.append(f'    - {name}: {value:.4g} ± {stderr}')

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
