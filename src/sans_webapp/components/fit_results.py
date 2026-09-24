"""
Fit results component for SANS webapp.

Contains rendering functions for displaying fit results,
parameter adjustments, and export functionality.
"""

import os
import tempfile
from typing import Any, cast

import numpy as np
import pandas as pd
import streamlit as st
from sans_fitter import SANSFitter

from sans_webapp.sans_analysis_utils import (
    calculate_residuals,
    evaluate_model,
    plot_fit_results,
)
from sans_webapp.sans_types import FitResult, ParamUpdate
from sans_webapp.ui_constants import (
    ADJUST_PARAMETER_HEADER,
    CHI_SQUARED_LABEL,
    FIT_CURVE_CSV_NAME,
    FIT_ENGINE_CAPTION,
    FIT_NOT_CONVERGED_WARNING,
    FIT_ON_BOUNDS_WARNING,
    FIT_REPORT_HEADER,
    FIT_RESULTS_HEADER,
    FIT_STATS_CAPTION,
    FIT_WARNINGS_HEADER,
    FITTED_PARAMETERS_HEADER,
    LOG_SCALE_LABEL,
    RESULTS_CSV_NAME,
    SAVE_FIT_CURVE_BUTTON,
    SAVE_RESULTS_BUTTON,
    SELECT_PARAMETER_LABEL,
    SHOW_RESIDUALS_LABEL,
    SLIDER_DEFAULT_MAX,
    SLIDER_DEFAULT_MIN,
    SLIDER_SCALE_MAX,
    SLIDER_SCALE_MIN,
    UPDATE_FROM_FIT_BUTTON,
)


def _get_fit_result() -> FitResult | None:
    """Return the fit result stored in session state, if it is a result dictionary."""
    if 'fit_result' not in st.session_state:
        return None
    fit_result = st.session_state.fit_result
    if not isinstance(fit_result, dict):
        return None
    return cast(FitResult, fit_result)


def render_fit_results(fitter: SANSFitter, param_updates: dict[str, ParamUpdate]) -> None:
    """
    Render the fit results section.

    Args:
        fitter: The SANSFitter instance
        param_updates: Current parameter updates
    """
    st.markdown('---')

    with st.expander(FIT_RESULTS_HEADER, expanded=True):
        _render_fit_warnings()

        # Plot options (placed before columns for stable layout)
        option_cols = st.columns(2)
        show_residuals = option_cols[0].checkbox(SHOW_RESIDUALS_LABEL, value=True)
        log_scale = option_cols[1].checkbox(LOG_SCALE_LABEL, value=True, key='results_log_scale')

        col1, col2 = st.columns([2, 1])

        with col1:
            try:
                # sans-fitter draws the figure: the last fit while it still matches
                # the current settings, the model at the current parameters once
                # something (e.g. the slider below) changed after the fit.
                fig = plot_fit_results(fitter, show_residuals=show_residuals, log_scale=log_scale)
                st.plotly_chart(fig, width='stretch', key='fit_results_chart')

            except Exception as e:
                st.error(f'Error plotting results: {str(e)}')

        with col2:
            _render_fit_statistics(fitter)
            _render_fitted_parameters_table(fitter)
            _render_parameter_slider(fitter)

        _render_fit_report(fitter)
        _render_export_section(fitter)


def _render_fit_warnings() -> None:
    """Show the warnings sans-fitter raised during the last fit (bounds, convergence, ...)."""
    if 'fit_warnings' not in st.session_state:
        return
    fit_warnings = st.session_state.fit_warnings
    if not fit_warnings:
        return
    st.markdown(FIT_WARNINGS_HEADER)
    for message in fit_warnings:
        st.warning(message)


def _render_fit_statistics(fitter: SANSFitter) -> None:
    """Render chi-squared, fit diagnostics and residual statistics."""
    fit_result = _get_fit_result()
    if fit_result is None:
        return

    # sans-fitter >= 0.4 separates the raw chi-squared from chi-squared/dof.
    # Display the reduced value, which is what the bumps engine used to report.
    reduced_chisq = fit_result.get('reduced_chisq', fit_result.get('chisq'))
    if reduced_chisq is None:
        return

    st.markdown(f'{CHI_SQUARED_LABEL}{_format_stat(reduced_chisq)}')

    if 'n_points' in fit_result:
        st.caption(
            FIT_STATS_CAPTION.format(
                n_points=fit_result.get('n_points'),
                n_free=fit_result.get('n_free'),
                dof=fit_result.get('dof'),
            )
        )
    if fit_result.get('engine'):
        st.caption(
            FIT_ENGINE_CAPTION.format(engine=fit_result['engine'], method=fit_result.get('method'))
        )

    converged = fit_result.get('converged')
    if converged is False:
        st.warning(FIT_NOT_CONVERGED_WARNING.format(message=fit_result.get('message') or ''))

    on_bounds = fit_result.get('on_bounds') or []
    if on_bounds:
        hits = ', '.join(f'{name} ({side})' for name, side in on_bounds)
        st.warning(FIT_ON_BOUNDS_WARNING.format(hits=hits))

    # Calculate and display residual statistics
    try:
        fit_i = evaluate_model(fitter)
        residuals = calculate_residuals(fitter.data.y, fit_i, fitter.data.dy)
        _render_residual_statistics(residuals)
    except Exception:
        pass  # Silently skip residual stats if calculation fails

    st.markdown('---')


def _format_stat(value: Any) -> str:
    """Format a goodness-of-fit number, showing 'n/a' when it is not finite."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 'n/a'
    return f'{number:.4f}' if np.isfinite(number) else 'n/a'


def _render_residual_statistics(residuals: np.ndarray) -> None:
    """Render residual statistics (NaN entries, i.e. unfitted points, are ignored)."""
    finite = np.asarray(residuals, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return
    st.markdown('**Residual Statistics**')
    col1, col2 = st.columns(2)
    with col1:
        st.metric('Mean', f'{np.mean(finite):.3f}')
    with col2:
        st.metric('Std Dev', f'{np.std(finite):.3f}')


def _was_varied(name: str, param_info: dict[str, Any], fitter: SANSFitter) -> bool:
    """Whether a fit-result entry belongs to a parameter the optimizer varied."""
    if 'fixed' in param_info:
        # sans-fitter >= 0.4 reports every parameter and flags the fixed ones.
        return not param_info['fixed']
    # Legacy result shape: infer from the fitter's vary flags.
    is_regular_varied = name in fitter.params and fitter.params[name]['vary']
    is_pd_param = name.endswith('_pd')
    return is_regular_varied or is_pd_param


def _render_fitted_parameters_table(fitter: SANSFitter) -> list[dict]:
    """Render the fitted parameters table and return the list of fitted params."""
    st.markdown(FITTED_PARAMETERS_HEADER)

    fitted_params = []
    fit_result = _get_fit_result()
    if fit_result is not None and 'parameters' in fit_result:
        for name, param_info in fit_result.get('parameters', {}).items():
            if not _was_varied(name, param_info, fitter):
                continue
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
        # Also show PD params that are set to vary
        if fitter.supports_polydispersity() and fitter.is_polydispersity_enabled():
            for pd_param in fitter.get_polydisperse_parameters():
                pd_config = fitter.get_pd_param(pd_param)
                if pd_config.get('vary', False):
                    fitted_params.append(
                        {
                            'Parameter': f'{pd_param}_pd',
                            'Value': f'{pd_config["pd"]:.4g}',
                            'Error': 'N/A',
                        }
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
    fit_result = _get_fit_result()
    if fit_result is not None and 'parameters' in fit_result:
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

        # Check if parameter selection changed
        param_changed = (
            'prev_selected_param' not in st.session_state
            or st.session_state.prev_selected_param != selected_param
        )

        if param_changed:
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

        # Determine default value based on whether parameter changed
        default_value = (
            current_value if param_changed else st.session_state.get('slider_value', current_value)
        )

        st.slider(
            f'{selected_param}',
            min_value=float(slider_min),
            max_value=float(slider_max),
            value=float(default_value),
            format='%.4g',
            key='slider_value',
            on_change=update_profile,
            label_visibility='collapsed',
        )

        st.caption(f'Range: {slider_min:.4g} to {slider_max:.4g}')

    if st.button(UPDATE_FROM_FIT_BUTTON):
        st.session_state.pending_update_from_fit = True
        st.rerun()


def _render_fit_report(fitter: SANSFitter) -> None:
    """Render sans-fitter's own fit report (statistics, parameters, correlations)."""
    try:
        report = fitter.get_fit_report()
        markdown = report.to_markdown()
    except Exception:
        # No fit in this session (e.g. result restored without a contract)
        return
    with st.expander(FIT_REPORT_HEADER, expanded=False):
        st.markdown(markdown)


def _build_results_csv(fitter: SANSFitter) -> str:
    """Build CSV string from fitter parameters."""
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

    # Add polydispersity parameters if enabled
    if fitter.supports_polydispersity() and fitter.is_polydispersity_enabled():
        for pd_param in fitter.get_polydisperse_parameters():
            pd_config = fitter.get_pd_param(pd_param)
            results_data.append(
                {
                    'Parameter': f'{pd_param}_pd',
                    'Value': pd_config['pd'],
                    'Min': 0.0,
                    'Max': 1.0,
                    'Fitted': pd_config.get('vary', False),
                }
            )
            results_data.append(
                {
                    'Parameter': f'{pd_param}_pd_type',
                    'Value': pd_config['pd_type'],
                    'Min': 'N/A',
                    'Max': 'N/A',
                    'Fitted': False,
                }
            )

    df_results = pd.DataFrame(results_data)
    return df_results.to_csv(index=False)


def _build_fit_curve_csv(fitter: SANSFitter) -> str | None:
    """Export the fitted curve and residuals through ``SANSFitter.save_results()``.

    Returns None when the fitter holds no fit result.
    """
    if getattr(fitter, 'fit_result', None) is None:
        return None
    fd, tmp_path = tempfile.mkstemp(suffix='.csv')
    os.close(fd)
    try:
        fitter.save_results(tmp_path)
        with open(tmp_path, encoding='utf-8') as handle:
            return handle.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _render_export_section(fitter: SANSFitter) -> None:
    """Render the export results section."""
    try:
        csv_data = _build_results_csv(fitter)
    except Exception as e:
        st.error(f'Error preparing results: {str(e)}')
        csv_data = 'Error generating CSV'

    export_cols = st.columns(2)
    with export_cols[0]:
        st.download_button(
            label=SAVE_RESULTS_BUTTON,
            data=csv_data,
            file_name=RESULTS_CSV_NAME,
            mime='text/csv',
        )

    try:
        curve_csv = _build_fit_curve_csv(fitter)
    except Exception as e:
        st.error(f'Error preparing fit curve: {str(e)}')
        curve_csv = None

    if curve_csv is not None:
        with export_cols[1]:
            st.download_button(
                label=SAVE_FIT_CURVE_BUTTON,
                data=curve_csv,
                file_name=FIT_CURVE_CSV_NAME,
                mime='text/csv',
            )
