"""
Fit results component for SANS webapp.

Contains rendering functions for displaying fit results,
parameter adjustments, and export functionality.
"""

from typing import cast

import pandas as pd
import streamlit as st
from sans_fitter import SANSFitter
from sasmodels.direct_model import DirectModel

from sans_analysis_utils import plot_data_and_fit
from sans_types import FitResult, ParamUpdate
from ui_constants import (
    ADJUST_PARAMETER_HEADER,
    CHI_SQUARED_LABEL,
    DOWNLOAD_RESULTS_LABEL,
    EXPORT_RESULTS_HEADER,
    FIT_RESULTS_HEADER,
    FITTED_PARAMETERS_HEADER,
    RESULTS_CSV_NAME,
    SAVE_RESULTS_BUTTON,
    SELECT_PARAMETER_LABEL,
    SLIDER_DEFAULT_MAX,
    SLIDER_DEFAULT_MIN,
    SLIDER_SCALE_MAX,
    SLIDER_SCALE_MIN,
    UPDATE_FROM_FIT_BUTTON,
)


def render_fit_results(fitter: SANSFitter, param_updates: dict[str, ParamUpdate]) -> None:
    """
    Render the fit results section.

    Args:
        fitter: The SANSFitter instance
        param_updates: Current parameter updates
    """
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
        _render_fit_statistics(fitter)
        _render_fitted_parameters_table(fitter)
        _render_parameter_slider(fitter)
        _render_export_section(fitter)


def _render_fit_statistics(fitter: SANSFitter) -> None:
    """Render chi-squared statistics."""
    if 'fit_result' in st.session_state and 'chisq' in st.session_state.fit_result:
        chi_squared = cast(FitResult, st.session_state.fit_result).get('chisq')
        if chi_squared is not None:
            st.markdown(f'{CHI_SQUARED_LABEL}{chi_squared:.4f}')
            st.markdown('---')


def _render_fitted_parameters_table(fitter: SANSFitter) -> list[dict]:
    """Render the fitted parameters table and return the list of fitted params."""
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
    else:
        st.info('No parameters were fitted')

    return fitted_params


def _render_parameter_slider(fitter: SANSFitter) -> None:
    """Render the parameter adjustment slider."""
    fitted_params = []
    if 'fit_result' in st.session_state and 'parameters' in st.session_state.fit_result:
        fit_result = cast(FitResult, st.session_state.fit_result)
        for name, param_info in fit_result.get('parameters', {}).items():
            if name in fitter.params and fitter.params[name]['vary']:
                value = param_info.get('value')
                if value is not None:
                    fitted_params.append({'Parameter': name, 'Value': value})
    else:
        for name, info in fitter.params.items():
            if info['vary']:
                fitted_params.append({'Parameter': name, 'Value': info['value']})

    if not fitted_params:
        return

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


def _render_export_section(fitter: SANSFitter) -> None:
    """Render the export results section."""
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
