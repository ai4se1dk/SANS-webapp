"""
Parameter components for SANS webapp.

Contains functions for rendering and managing model parameters:
- Parameter table rendering
- Applying presets
- Applying fit results
- Building parameter updates
- Polydispersity configuration (tabbed interface)
"""

from typing import cast

import streamlit as st
from sans_fitter import SANSFitter

from sans_webapp.sans_types import FitResult, ParamInfo, ParamUpdate, PDUpdate
from sans_webapp.services.session_state import clamp_for_display
from sans_webapp.ui_constants import (
    PARAM_TAB_BASIC,
    PARAM_TAB_POLYDISPERSITY,
    PARAMETER_COLUMNS_LABELS,
    PARAMETER_FIT_LABEL,
    PARAMETER_MAX_LABEL,
    PARAMETER_MIN_LABEL,
    PARAMETER_UPDATE_BUTTON,
    PARAMETER_VALUE_LABEL,
    PARAMETERS_HEADER_PREFIX,
    PARAMETERS_HELP_TEXT,
    PD_AVAILABLE_PARAMS_LABEL,
    PD_DISTRIBUTION_TYPES,
    PD_ENABLE_HELP,
    PD_ENABLE_LABEL,
    PD_INFO_HEADER,
    PD_INFO_TEXT,
    PD_N_HELP,
    PD_N_LABEL,
    PD_NOT_SUPPORTED,
    PD_SUCCESS_UPDATED,
    PD_TABLE_COLUMNS,
    PD_TYPE_HELP,
    PD_TYPE_LABEL,
    PD_UPDATE_BUTTON,
    PD_VARY_LABEL,
    PD_WIDTH_HELP,
    PD_WIDTH_LABEL,
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
            fitted_value = fit_param_info.get('value')
            if fitted_value is None:
                continue

            if param_name in params:
                # Regular parameter
                st.session_state[f'value_{param_name}'] = clamp_for_display(float(fitted_value))
                fitter.set_param(param_name, value=fitted_value)
            elif param_name.endswith('_pd'):
                # Polydispersity parameter - update fitter and session state
                base_param = param_name[:-3]  # Remove '_pd' suffix
                if fitter.supports_polydispersity():
                    pd_params = fitter.get_polydisperse_parameters()
                    if base_param in pd_params:
                        fitter.set_pd_param(base_param, pd_width=fitted_value)
                        # Update session state for PD width
                        st.session_state[f'pd_width_{base_param}'] = float(fitted_value)
                        # Also update pd_updates if it exists
                        if (
                            'pd_updates' in st.session_state
                            and base_param in st.session_state.pd_updates
                        ):
                            st.session_state.pd_updates[base_param]['pd_width'] = float(
                                fitted_value
                            )
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
    # Create 5 explicit columns: Parameter, Value, Min, Max, Fit?
    # Use explicit widths to ensure alignment
    col_widths = [2.5, 1, 1, 1, 0.5]

    # Header row
    header_cols = st.columns(col_widths)
    header_cols[0].markdown(PARAMETER_COLUMNS_LABELS[0])  # Parameter
    header_cols[1].markdown(PARAMETER_COLUMNS_LABELS[1])  # Value
    header_cols[2].markdown(PARAMETER_COLUMNS_LABELS[2])  # Min
    header_cols[3].markdown(PARAMETER_COLUMNS_LABELS[3])  # Max
    header_cols[4].markdown(PARAMETER_COLUMNS_LABELS[4])  # Fit?

    param_updates: dict[str, ParamUpdate] = {}

    for param_name, param_info in params.items():
        cols = st.columns(col_widths)

        # Session state keys
        value_key = f'value_{param_name}'
        min_key = f'min_{param_name}'
        max_key = f'max_{param_name}'
        vary_key = f'vary_{param_name}'

        # Initialize session state if not set
        if vary_key not in st.session_state:
            st.session_state[vary_key] = param_info['vary']
        if value_key not in st.session_state:
            st.session_state[value_key] = clamp_for_display(float(param_info['value']))
        if min_key not in st.session_state:
            st.session_state[min_key] = clamp_for_display(float(param_info['min']))
        if max_key not in st.session_state:
            st.session_state[max_key] = clamp_for_display(float(param_info['max']))

        # Column 0: Parameter name
        with cols[0]:
            st.text(param_name)
            description = param_info.get('description')
            if description:
                st.caption(description[:50])

        # Column 1: Value
        with cols[1]:
            value = st.number_input(
                PARAMETER_VALUE_LABEL,
                format='%g',
                key=value_key,
                label_visibility='collapsed',
            )

        # Column 2: Min
        with cols[2]:
            min_val = st.number_input(
                PARAMETER_MIN_LABEL,
                format='%g',
                key=min_key,
                label_visibility='collapsed',
            )

        # Column 3: Max
        with cols[3]:
            max_val = st.number_input(
                PARAMETER_MAX_LABEL,
                format='%g',
                key=max_key,
                label_visibility='collapsed',
            )

        # Column 4: Fit? checkbox
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


def render_polydispersity_table(fitter: SANSFitter) -> dict[str, PDUpdate]:
    """
    Render the polydispersity parameter table.

    Args:
        fitter: The SANSFitter instance

    Returns:
        Dictionary of polydispersity updates keyed by parameter name
    """
    pd_params = fitter.get_polydisperse_parameters()
    pd_updates: dict[str, PDUpdate] = {}

    # Table header
    pd_cols = st.columns([2, 1.5, 1, 1.5, 1])
    for i, label in enumerate(PD_TABLE_COLUMNS):
        pd_cols[i].markdown(label)

    for param_name in pd_params:
        # Get current PD configuration
        pd_config = fitter.get_pd_param(param_name)

        cols = st.columns([2, 1.5, 1, 1.5, 1])

        with cols[0]:
            st.text(param_name)

        # Session state keys
        pd_width_key = f'pd_width_{param_name}'
        pd_n_key = f'pd_n_{param_name}'
        pd_type_key = f'pd_type_{param_name}'
        pd_vary_key = f'pd_vary_{param_name}'

        # Initialize session state if not present
        if pd_width_key not in st.session_state:
            st.session_state[pd_width_key] = float(pd_config['pd'])
        if pd_n_key not in st.session_state:
            st.session_state[pd_n_key] = int(pd_config['pd_n'])
        if pd_type_key not in st.session_state:
            st.session_state[pd_type_key] = pd_config['pd_type']
        if pd_vary_key not in st.session_state:
            st.session_state[pd_vary_key] = pd_config.get('vary', False)

        with cols[1]:
            pd_width = st.number_input(
                PD_WIDTH_LABEL,
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                format='%.3f',
                key=pd_width_key,
                label_visibility='collapsed',
                help=PD_WIDTH_HELP,
            )

        with cols[2]:
            pd_n = st.number_input(
                PD_N_LABEL,
                min_value=5,
                max_value=100,
                step=5,
                key=pd_n_key,
                label_visibility='collapsed',
                help=PD_N_HELP,
            )

        with cols[3]:
            # Find current type index
            try:
                current_idx = PD_DISTRIBUTION_TYPES.index(st.session_state[pd_type_key])
            except ValueError:
                current_idx = 0

            pd_type = st.selectbox(
                PD_TYPE_LABEL,
                options=PD_DISTRIBUTION_TYPES,
                index=current_idx,
                key=pd_type_key,
                label_visibility='collapsed',
                help=PD_TYPE_HELP,
            )

        with cols[4]:
            pd_vary = st.checkbox(
                PD_VARY_LABEL,
                key=pd_vary_key,
                label_visibility='collapsed',
            )

        # Warn if PD width is high (may cause numerical instability)
        if pd_width > 0.5:
            st.warning(
                f'⚠️ PD Width for {param_name} is {pd_width:.2f}. '
                'Values > 0.5 may cause numerical instability.'
            )

        pd_updates[param_name] = {
            'pd_width': pd_width,
            'pd_n': int(pd_n),  # Explicit int cast from number_input
            'pd_type': pd_type,
            'vary': pd_vary,
        }

    return pd_updates


def apply_pd_updates(fitter: SANSFitter, pd_updates: dict[str, PDUpdate]) -> None:
    """
    Apply polydispersity updates to the fitter.

    Args:
        fitter: The SANSFitter instance
        pd_updates: Dictionary of PD updates keyed by parameter name.
                    Note: 'pd_width' in PDUpdate maps to fitter's 'pd' parameter.
    """
    for param_name, updates in pd_updates.items():
        fitter.set_pd_param(
            param_name,
            pd_width=updates['pd_width'],
            pd_n=updates['pd_n'],
            pd_type=updates['pd_type'],
            vary=updates['vary'],
        )


def render_polydispersity_tab(fitter: SANSFitter) -> None:
    """
    Render the polydispersity configuration tab.

    Args:
        fitter: The SANSFitter instance
    """
    # Check if model supports polydispersity
    if not fitter.supports_polydispersity():
        st.info(PD_NOT_SUPPORTED)
        return

    pd_params = fitter.get_polydisperse_parameters()

    # Validate stored pd_updates match current model's PD parameters
    # This handles model changes that have different polydisperse parameters
    if 'pd_updates' in st.session_state:
        current_pd_params = set(pd_params)
        stored_params = set(st.session_state.pd_updates.keys())
        if stored_params != current_pd_params:
            del st.session_state['pd_updates']

    # Master enable toggle
    pd_enabled_key = 'pd_enabled'
    if pd_enabled_key not in st.session_state:
        st.session_state[pd_enabled_key] = fitter.is_polydispersity_enabled()

    pd_enabled = st.checkbox(
        PD_ENABLE_LABEL,
        key=pd_enabled_key,
        help=PD_ENABLE_HELP,
    )

    # Sync with fitter
    if pd_enabled != fitter.is_polydispersity_enabled():
        fitter.enable_polydispersity(pd_enabled)

    if not pd_enabled:
        st.caption('Polydispersity is disabled. Enable it to configure size distributions.')
        # Show info section
        with st.expander(PD_INFO_HEADER):
            st.markdown(PD_INFO_TEXT)
        return

    st.markdown(PD_AVAILABLE_PARAMS_LABEL.format(count=len(pd_params)))

    # Render PD parameter table in a form
    with st.form('pd_form'):
        pd_updates = render_polydispersity_table(fitter)
        submitted = st.form_submit_button(PD_UPDATE_BUTTON)

    if submitted:
        apply_pd_updates(fitter, pd_updates)
        st.session_state.pd_updates = pd_updates
        st.success(PD_SUCCESS_UPDATED)
    elif 'pd_updates' not in st.session_state:
        # Initialize from current fitter state, not stale form values
        st.session_state.pd_updates = {
            param: {
                'pd_width': fitter.get_pd_param(param)['pd'],
                'pd_n': fitter.get_pd_param(param)['pd_n'],
                'pd_type': fitter.get_pd_param(param)['pd_type'],
                'vary': fitter.get_pd_param(param).get('vary', False),
            }
            for param in pd_params
        }

    # Show info section
    with st.expander(PD_INFO_HEADER):
        st.markdown(PD_INFO_TEXT)


def render_basic_parameters_tab(
    fitter: SANSFitter, params: dict[str, ParamInfo]
) -> dict[str, ParamUpdate]:
    """
    Render the basic parameters tab content.

    Args:
        fitter: The SANSFitter instance
        params: Dictionary of parameter info

    Returns:
        The current parameter updates
    """
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


def render_parameter_configuration(fitter: SANSFitter) -> dict[str, ParamUpdate]:
    """
    Render the full parameter configuration section with tabs.

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

    # Create tabbed interface
    # Only show polydispersity tab if model supports it
    if fitter.supports_polydispersity():
        basic_tab, pd_tab = st.tabs([PARAM_TAB_BASIC, PARAM_TAB_POLYDISPERSITY])

        with basic_tab:
            param_updates = render_basic_parameters_tab(fitter, params)

        with pd_tab:
            render_polydispersity_tab(fitter)
    else:
        # No polydispersity support - just render basic parameters
        param_updates = render_basic_parameters_tab(fitter, params)

    return param_updates
