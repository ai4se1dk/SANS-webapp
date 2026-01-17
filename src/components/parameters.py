"""
Parameter components for SANS webapp.

Contains functions for rendering and managing model parameters:
- Parameter table rendering
- Applying presets
- Applying fit results
- Building parameter updates
"""

from typing import cast

import streamlit as st
from sans_fitter import SANSFitter

from sans_types import FitResult, ParamInfo, ParamUpdate
from services.session_state import clamp_for_display
from ui_constants import (
    PARAMETER_COLUMNS_LABELS,
    PARAMETER_FIT_LABEL,
    PARAMETER_MAX_LABEL,
    PARAMETER_MIN_LABEL,
    PARAMETER_UPDATE_BUTTON,
    PARAMETER_VALUE_LABEL,
    PARAMETERS_HEADER_PREFIX,
    PARAMETERS_HELP_TEXT,
    PRESET_FIT_ALL,
    PRESET_FIT_SCALE_BACKGROUND,
    PRESET_FIX_ALL,
    PRESET_HEADER,
    SUCCESS_PARAMS_UPDATED,
)


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

    # Update param_updates to reflect the preset changes for fitting
    if 'param_updates' in st.session_state:
        for param_name in params.keys():
            if param_name in st.session_state.param_updates:
                st.session_state.param_updates[param_name]['vary'] = fitter.params[param_name][
                    'vary'
                ]


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

    # Use loop as recommended in refactoring
    for i, label in enumerate(PARAMETER_COLUMNS_LABELS):
        param_cols[i].markdown(label)

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


def render_parameter_configuration(fitter: SANSFitter) -> dict[str, ParamUpdate]:
    """
    Render the full parameter configuration section.

    Args:
        fitter: The SANSFitter instance

    Returns:
        The current parameter updates
    """
    st.subheader(f'{PARAMETERS_HEADER_PREFIX}{st.session_state.current_model}')

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

    return param_updates
