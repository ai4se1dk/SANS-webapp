"""
AI Chat service for SANS webapp.

Contains functions for AI-powered model suggestion and chat functionality.
"""

from typing import Optional, cast

import numpy as np
import streamlit as st
from sans_fitter import SANSFitter, get_all_models
from sasmodels.direct_model import DirectModel

from sans_webapp.openai_client import create_chat_completion
from sans_webapp.sans_analysis_utils import (
    analyze_data_for_ai_suggestion,
    suggest_models_simple,
)
from sans_webapp.sans_types import FitResult, ParamInfo
from sans_webapp.ui_constants import WARNING_NO_API_KEY


def _send_chat_message_openai(user_message: str, api_key: Optional[str], fitter: SANSFitter) -> str:
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

            # Add post-fit profile (model curve) if possible
            if fitter.data is not None and fitter.kernel is not None and fitter.params:
                try:
                    param_values = {name: info['value'] for name, info in fitter.params.items()}
                    calculator = DirectModel(fitter.data, fitter.kernel)
                    fit_i = calculator(**param_values)
                    q_vals = fitter.data.x
                    sample_count = min(50, len(q_vals))
                    sample_idx = np.linspace(0, len(q_vals) - 1, num=sample_count, dtype=int)
                    context_parts.append('  Post-fit profile (Q, I_fit):')
                    for idx in sample_idx:
                        context_parts.append(f'    - {q_vals[idx]:.6f}, {fit_i[idx]:.6e}')
                except Exception:
                    pass

            # Add fitted parameter values with uncertainties
            if 'parameters' in fit_result:
                context_parts.append('  Fitted parameter values:')
                for name, param_info in fit_result['parameters'].items():
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


"""
AI Chat services for SANS webapp.

Provides functions for AI-assisted SANS model analysis using Claude with MCP tools.
"""

import os
from typing import Any, Optional

import numpy as np
import streamlit as st
from sans_fitter import SANSFitter, get_all_models

from sans_webapp.mcp_server import set_fitter, set_state_accessor
from sans_webapp.services.claude_mcp_client import (
    ClaudeMCPClient,
    get_claude_client,
    reset_client,
)

# System prompt for SANS model suggestions (used for simple suggestions without tools)
SUGGEST_MODELS_SYSTEM_PROMPT = """You are a SANS (Small-Angle Neutron Scattering) expert.
Based on the scattering data characteristics provided, suggest appropriate sasmodels models.
Return ONLY a comma-separated list of model names, nothing else.
Available models include: sphere, cylinder, ellipsoid, core_shell_sphere, 
core_shell_cylinder, gaussian_peak, power_law, fractal, etc."""


def _build_context(fitter: SANSFitter) -> str:
    """Build context string from the current fitter state."""
    context_parts = []

    # Data info
    if hasattr(fitter, 'data') and fitter.data is not None:
        data = fitter.data
        context_parts.append(
            f'Data loaded: {len(data.x)} points, Q range [{data.x.min():.4f}, {data.x.max():.4f}]'
        )
    else:
        context_parts.append('No data loaded')

    # Model info
    if hasattr(fitter, 'model') and fitter.model is not None:
        model_name = fitter.model.name if hasattr(fitter.model, 'name') else 'Unknown'
        context_parts.append(f'Current model: {model_name}')

        # Parameters
        if hasattr(fitter, 'params') and fitter.params:
            param_info = []
            for name, param in fitter.params.items():
                value = getattr(param, 'value', 'N/A')
                vary = getattr(param, 'vary', True)
                param_info.append(f'  {name}: {value} (vary: {vary})')
            context_parts.append('Parameters:\n' + '\n'.join(param_info))
    else:
        context_parts.append('No model selected')

    # Fit results
    if hasattr(fitter, 'result') and fitter.result is not None:
        if hasattr(fitter.result, 'redchi'):
            context_parts.append(f'Last fit chi-square: {fitter.result.redchi:.4f}')

    # AI tools status
    ai_tools_enabled = getattr(st.session_state, 'ai_tools_enabled', False)
    context_parts.append(f'AI tools enabled: {ai_tools_enabled}')

    return '\n'.join(context_parts)


def _ensure_mcp_initialized(fitter: SANSFitter) -> None:
    """Ensure MCP server has access to the fitter and session state."""
    set_fitter(fitter)
    set_state_accessor(st.session_state)


def suggest_models_ai(
    x_data: np.ndarray, y_data: np.ndarray, api_key: Optional[str] = None
) -> list[str]:
    """
    Use AI to suggest appropriate SANS models based on data characteristics.

    Args:
        x_data: Q values (scattering vector)
        y_data: Intensity values
        api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env var)

    Returns:
        List of suggested model names
    """
    try:
        # Try to use Claude client
        client = get_claude_client(api_key)

        # Build data description
        data_desc = f"""Q range: {x_data.min():.4f} to {x_data.max():.4f}
I(Q) range: {y_data.min():.4e} to {y_data.max():.4e}
Number of points: {len(x_data)}
Log-log slope at low Q: {np.polyfit(np.log(x_data[:10]), np.log(y_data[:10]), 1)[0]:.2f}
"""

        # Use simple chat for suggestions (no tools needed)
        prompt = f"""Based on this SANS scattering data, suggest 3-5 appropriate sasmodels models.
Return ONLY a comma-separated list of model names, nothing else.

{data_desc}

Available models include: sphere, cylinder, ellipsoid, core_shell_sphere, 
core_shell_cylinder, gaussian_peak, power_law, fractal, etc."""

        response = client.simple_chat(prompt)
        suggestions_text = response.strip()
        suggestions = [s.strip() for s in suggestions_text.split(',')]

        # Validate against available models
        available = get_all_models()
        valid_suggestions = [s for s in suggestions if s in available]

        return valid_suggestions if valid_suggestions else ['sphere', 'cylinder']

    except Exception as e:
        print(f'AI suggestion error: {e}')
        return ['sphere', 'cylinder', 'ellipsoid']


def _send_chat_message_claude(
    prompt: str, api_key: Optional[str], fitter: SANSFitter
) -> str:
    """
    Send a chat message and get AI response with MCP tool support.

    Args:
        prompt: User's message
        api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env var)
        fitter: Current SANSFitter instance for context

    Returns:
        AI response text
    """
    try:
        # Ensure MCP server has access to fitter and state
        _ensure_mcp_initialized(fitter)

        # Get or create Claude client
        try:
            client = get_claude_client(api_key)
        except ValueError:
            # API key not set - reset and try again with provided key
            if api_key:
                reset_client()
                client = get_claude_client(api_key)
            else:
                return "Error: Anthropic API key not configured. Please enter your API key in the sidebar."

        # Build context from current fitter state
        context = _build_context(fitter)

        # Get conversation history from session state
        conversation_history = []
        if hasattr(st.session_state, 'chat_history'):
            # Convert to format expected by Claude client
            for msg in st.session_state.chat_history:
                conversation_history.append({
                    'role': msg['role'],
                    'content': msg['content'],
                })

        # Send message with tool support
        response, tool_invocations = client.chat(
            user_message=prompt,
            conversation_history=conversation_history,
            context=context,
        )

        # Check if any tools were invoked that require UI refresh
        if tool_invocations:
            # Check if needs_rerun was set by any tool
            if getattr(st.session_state, 'needs_rerun', False):
                # Will be handled by the calling code
                pass

            # Append tool invocation info to response if tools were used
            tool_summary = []
            for invocation in tool_invocations:
                tool_name = invocation['tool_name']
                tool_summary.append(f"[Used tool: {tool_name}]")

            if tool_summary:
                response = response + "\n\n" + "\n".join(tool_summary)

        return response

    except Exception as e:
        return f'Error: {str(e)}'


def send_chat_message(user_message: str, api_key: Optional[str], fitter: SANSFitter) -> str:
    """
    Send a chat message and return an AI response.

    Uses Claude MCP tools when AI tools are enabled in session state; otherwise falls back
    to the legacy OpenAI-based implementation for backwards compatibility with tests.
    """
    try:
        # Check explicitly for presence so tests that mock `in` work correctly
        if 'ai_tools_enabled' in st.session_state and st.session_state.ai_tools_enabled:
            return _send_chat_message_claude(user_message, api_key, fitter)
    except Exception:
        # If session_state access fails, fall back to legacy behavior
        pass

    # If AI tools are disabled, and the user's message looks like a request to change
    # state (set/update/change/run), provide a short actionable prompt asking them to
    # enable AI tools rather than silently falling back to the OpenAI-only path.
    lowered = user_message.lower()
    mutation_keywords = (
        'set ',
        'change ',
        'update ',
        'enable ',
        'run fit',
        'run-fit',
        'set parameter',
        'set-parameter',
    )
    if any(k in lowered for k in mutation_keywords):
        return (
            "I can make that change automatically if you enable 'AI Tools' in the sidebar "
            "(🔧 Enable AI Tools). Please toggle it on and send the message again."
        )

    return _send_chat_message_openai(user_message, api_key, fitter)


def response_requests_enable_tools(response_text: str) -> bool:
    """Detect whether a response is prompting the user to enable AI tools.

    This is used by the UI to surface an inline button so the user can enable tools
    directly from the assistant's message.
    """
    if not response_text:
        return False
    lowered = response_text.lower()
    # Basic heuristic: contains 'enable' and 'ai tools' near each other
    return 'enable' in lowered and 'ai tools' in lowered


def send_chat_message_with_tools(
    prompt: str,
    api_key: Optional[str],
    fitter,
    conversation_history: Optional[list[dict[str, str]]] = None,
) -> tuple[str, list[str], bool]:
    """
    Send a chat message with full tool invocation details.

    Args:
        prompt: User's message
        api_key: Anthropic API key
        fitter: Current SANSFitter instance
        conversation_history: Previous messages

    Returns:
        Tuple of (response_text, tool_invocations, needs_rerun)
    """
    _ensure_mcp_initialized(fitter)

    try:
        client = get_claude_client(api_key)
    except ValueError:
        if api_key:
            reset_client()
            client = get_claude_client(api_key)
        else:
            return (
                "Error: Anthropic API key not configured.",
                [],
                False,
            )

    context = _build_context(fitter)

    chat_result = client.chat(
        user_message=prompt,
        conversation_history=conversation_history,
        context=context,
    )

    # Client.chat may return either (response_text, tool_list) or just response_text
    if isinstance(chat_result, tuple) or isinstance(chat_result, list):
        response, tool_invocations = chat_result
    else:
        response = chat_result
        tool_invocations = []

    # Normalize tool invocations to list of tool-name strings for test compatibility
    normalized_tools: list[str] = []
    if isinstance(tool_invocations, list):
        for t in tool_invocations:
            if isinstance(t, str):
                normalized_tools.append(t)
            elif isinstance(t, dict) and 'tool_name' in t:
                normalized_tools.append(t['tool_name'])
            elif isinstance(t, (list, tuple)) and len(t) > 0:
                # If some clients return a tuple-like (name, ...)
                normalized_tools.append(t[0])

    tool_invocations = normalized_tools

    needs_rerun = getattr(st.session_state, 'needs_rerun', False)
    if needs_rerun:
        st.session_state.needs_rerun = False  # Reset the flag

    return response, tool_invocations, needs_rerun

    return response, tool_invocations, needs_rerun
