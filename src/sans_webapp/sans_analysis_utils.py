"""
SANS Data Analysis Utility Functions

Shared utility functions for SANS data analysis that can be used by both
the Streamlit web application and command-line scripts without importing Streamlit.
"""

import warnings
from typing import Any, Optional

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sans_fitter import SANSFitter, get_all_models
from sans_fitter.data.loader import has_real_data

# Re-export get_all_models for backwards compatibility
__all__ = [
    'get_all_models',
    'analyze_data_for_ai_suggestion',
    'suggest_models_simple',
    'plot_data_and_fit',
    'calculate_residuals',
    'plot_data_fit_and_residuals',
    'evaluate_model',
    'data_column_summary',
    'run_fit_with_warnings',
    'format_fit_summary',
    'format_fit_parameters',
    'describe_fitter_state',
]


# =============================================================================
# sans-fitter integration helpers (Streamlit-free)
# =============================================================================


def evaluate_model(fitter: SANSFitter) -> np.ndarray:
    """
    Evaluate the model at the current parameter values on the data grid.

    Delegates to ``SANSFitter.calculate()`` so the curve is computed exactly as
    during a fit: polydispersity, parameter links, structure factors and the
    active resolution setting are all applied. The result has one entry per
    data point, with NaN where a point is excluded from the fit (outside the
    fit Q range, masked or NaN), so it can be plotted directly against
    ``fitter.data.x``.

    Args:
        fitter: SANSFitter instance with data and a model loaded

    Returns:
        Model intensity array aligned with ``fitter.data.x``
    """
    return np.asarray(fitter.calculate(), dtype=float)


def data_column_summary(data: Any) -> dict[str, bool]:
    """
    Report which optional columns a loaded dataset really carries.

    sasdata zero-fills optional columns that are absent from the input file,
    so ``data.dy`` / ``data.dx`` being present does not mean they hold values.

    Args:
        data: A sasdata Data1D object (``fitter.data``)

    Returns:
        ``{'has_dy': bool, 'has_dx': bool}`` for intensity uncertainties (dI)
        and Q resolution (dQ) respectively.
    """
    summary = {'has_dy': False, 'has_dx': False}
    for key, attr in (('has_dy', 'dy'), ('has_dx', 'dx')):
        try:
            summary[key] = bool(has_real_data(getattr(data, attr, None)))
        except Exception:
            # Not a real dataset (e.g. a test double): treat the column as absent
            summary[key] = False
    return summary


def run_fit_with_warnings(
    fitter: SANSFitter,
    engine: str = 'bumps',
    method: Optional[str] = None,
    **kwargs: Any,
) -> tuple[dict[str, Any], list[str]]:
    """
    Run ``fitter.fit()`` and capture the warnings sans-fitter emits.

    sans-fitter >= 0.4 reports parameters resting on a bound, non-convergence,
    scale degeneracy and unweighted points through ``warnings.warn`` rather
    than through its logger, so a UI has to record them to show them.

    Args:
        fitter: Configured SANSFitter (data, model and parameters set)
        engine: 'bumps' or 'lmfit'
        method: Engine-specific optimizer name (engine default when None)
        **kwargs: Extra arguments forwarded to ``fitter.fit()``

    Returns:
        Tuple of (fit result dictionary, list of warning messages)
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        result = fitter.fit(engine=engine, method=method, **kwargs)
    messages = [
        str(entry.message)
        for entry in caught
        if issubclass(entry.category, UserWarning)
        and not issubclass(entry.category, DeprecationWarning)
    ]
    return result, messages


def _format_number(value: Any, fmt: str = '.4f') -> str:
    """Format a number for display, showing 'n/a' for missing or non-finite values."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 'n/a'
    if not np.isfinite(number):
        return 'n/a'
    return format(number, fmt)


def format_fit_summary(fit_result: dict[str, Any]) -> list[str]:
    """
    Summarize the goodness-of-fit block of a fit result as text lines.

    Understands the sans-fitter >= 0.4 result shape (``reduced_chisq``,
    ``n_points``, ``n_free``, ``dof``, ``converged``, ``on_bounds``) and
    degrades gracefully for a dictionary carrying only ``chisq``.

    Args:
        fit_result: Dictionary returned by ``SANSFitter.fit()``

    Returns:
        List of human-readable lines (no trailing newlines)
    """
    lines: list[str] = []
    engine = fit_result.get('engine')
    method = fit_result.get('method')
    if engine:
        lines.append(f'Engine: {engine}' + (f' / {method}' if method else ''))

    if 'reduced_chisq' in fit_result:
        lines.append(
            f'Reduced chi-squared (chi2/dof): {_format_number(fit_result["reduced_chisq"])}'
        )
        lines.append(f'Chi-squared (raw): {_format_number(fit_result.get("chisq"))}')
    elif 'chisq' in fit_result:
        lines.append(f'Chi-squared: {_format_number(fit_result["chisq"])}')

    if 'n_points' in fit_result:
        lines.append(
            f'Points fitted: {fit_result.get("n_points")}, free parameters: '
            f'{fit_result.get("n_free")}, degrees of freedom: {fit_result.get("dof")}'
        )

    converged = fit_result.get('converged')
    if converged is True:
        lines.append('Converged: yes')
    elif converged is False:
        message = fit_result.get('message') or 'no message'
        lines.append(f'Converged: NO ({message})')

    on_bounds = fit_result.get('on_bounds') or []
    if on_bounds:
        hits = ', '.join(f'{name} ({side})' for name, side in on_bounds)
        lines.append(f'Parameters at a bound: {hits}')

    return lines


def format_fit_parameters(fit_result: dict[str, Any], include_fixed: bool = False) -> list[str]:
    """
    Format the ``parameters`` block of a fit result as text lines.

    Args:
        fit_result: Dictionary returned by ``SANSFitter.fit()``
        include_fixed: Also list parameters the optimizer did not vary

    Returns:
        List of lines such as ``'  - radius: 62.3 ± 1.5'``
    """
    lines: list[str] = []
    for name, info in fit_result.get('parameters', {}).items():
        fixed = info.get('fixed', False)
        if fixed and not include_fixed:
            continue
        formatted = info.get('formatted')
        if not formatted:
            value = info.get('value')
            stderr = info.get('stderr')
            if isinstance(stderr, (int, float)) and stderr:
                formatted = f'{value:.6g} ± {stderr:.4g}'
            else:
                formatted = f'{value:.6g}' if isinstance(value, (int, float)) else str(value)
        suffix = ''
        if fixed and '(fixed)' not in formatted and '(linked)' not in formatted:
            suffix = ' (fixed)'
        lines.append(f'  - {name}: {formatted}{suffix}')
    return lines


def _safe_call(fitter: Any, method_name: str, *args: Any, **kwargs: Any) -> Any:
    """Call ``fitter.<method_name>`` if it exists; return None on any failure."""
    method = getattr(fitter, method_name, None)
    if not callable(method):
        return None
    try:
        return method(*args, **kwargs)
    except Exception:
        return None


def _describe_data(fitter: Any) -> list[str]:
    """Lines about the loaded dataset, its columns, fit Q range and resolution."""
    data = getattr(fitter, 'data', None)
    if data is None:
        return ['Data: Not loaded']

    lines: list[str] = []
    x = np.asarray(data.x, dtype=float)
    lines.append(f'Data: {len(x)} points, Q range [{np.nanmin(x):.4f}, {np.nanmax(x):.4f}]')
    columns = data_column_summary(data)
    lines.append(
        f'Data columns: dI {"present" if columns["has_dy"] else "absent"}, '
        f'dQ {"present" if columns["has_dx"] else "absent"}'
    )

    q_range = _safe_call(fitter, 'get_q_range')
    if isinstance(q_range, (tuple, list)) and len(q_range) == 2:
        lo, hi = float(q_range[0]), float(q_range[1])
        n_in_range = int(np.sum((x >= lo) & (x <= hi)))
        lines.append(f'Fit Q range: [{lo:.4g}, {hi:.4g}] ({n_in_range} of {len(x)} points)')

    resolution = _safe_call(fitter, 'get_resolution')
    if isinstance(resolution, dict) and resolution.get('mode'):
        mode = resolution['mode']
        detail = ''
        if mode == 'pinhole' and resolution.get('dq_over_q') is not None:
            detail = f' (dQ/Q = {resolution["dq_over_q"]})'
        elif mode == 'slit':
            detail = (
                f' (slit length = {resolution.get("slit_length")}, '
                f'slit width = {resolution.get("slit_width")})'
            )
        lines.append(f'Resolution mode: {mode}{detail}')
    return lines


def _describe_model(fitter: Any) -> list[str]:
    """Lines about the model, its parameters, links, structure factor and PD."""
    if getattr(fitter, 'kernel', None) is None:
        return ['Model: Not selected']

    lines: list[str] = []
    model_name = getattr(fitter, 'model_name', None) or 'Unknown'
    lines.append(f'Model: {model_name}')

    structure_factor = _safe_call(fitter, 'get_structure_factor')
    if isinstance(structure_factor, str) and structure_factor:
        lines.append(f'Structure factor: {structure_factor}')

    components = _safe_call(fitter, 'get_components')
    if isinstance(components, (list, tuple)) and components:
        lines.append(
            'Composite components: '
            + ', '.join(f'{moniker} ({part})' for _prefix, moniker, part in components)
        )

    params = getattr(fitter, 'params', None)
    if isinstance(params, dict) and params:
        lines.append('Parameters:')
        for name, param in params.items():
            value = param.get('value', 'N/A')
            vary = param.get('vary', True)
            lines.append(f'  - {name}: {value} (vary: {vary})')

    links = _safe_call(fitter, 'get_links')
    if isinstance(links, dict) and links:
        lines.append(
            'Linked parameters: '
            + ', '.join(f'{follower} -> {target}' for follower, target in links.items())
        )

    if _safe_call(fitter, 'supports_polydispersity') is True:
        enabled = _safe_call(fitter, 'is_polydispersity_enabled') is True
        lines.append(f'Polydispersity: {"enabled" if enabled else "disabled"}')
        pd_names = _safe_call(fitter, 'get_polydisperse_parameters')
        for base in pd_names if isinstance(pd_names, (list, tuple)) else []:
            config = _safe_call(fitter, 'get_pd_param', base)
            if not isinstance(config, dict):
                continue
            if config.get('pd', 0) > 0 or config.get('vary', False):
                lines.append(
                    f'  - {base}_pd: width={config.get("pd")} type={config.get("pd_type")} '
                    f'n={config.get("pd_n")} (vary: {config.get("vary", False)})'
                )
    return lines


def _describe_last_fit(fitter: Any) -> list[str]:
    """Lines summarizing the last fit result held by the fitter, if any."""
    fit_result = getattr(fitter, 'fit_result', None)
    if not isinstance(fit_result, dict) or not fit_result:
        return []
    return ['Last fit:'] + [f'  {line}' for line in format_fit_summary(fit_result)]


def describe_fitter_state(fitter: Any) -> list[str]:
    """
    Describe a fitter's data, model, parameters and last fit as text lines.

    Shared by the MCP ``get-current-state`` tool and the AI chat context. Every
    accessor is optional and every section is guarded, so the description also
    works for partially configured fitters and test doubles.

    Args:
        fitter: SANSFitter (or compatible) instance

    Returns:
        List of lines describing the current state
    """
    lines: list[str] = []
    for section, fallback in (
        (_describe_data, 'Data: unavailable'),
        (_describe_model, 'Model: unavailable'),
        (_describe_last_fit, None),
    ):
        try:
            lines.extend(section(fitter))
        except Exception:
            if fallback is not None:
                lines.append(fallback)
    return lines


# =============================================================================
# Heuristic model suggestion
# =============================================================================


def analyze_data_for_ai_suggestion(q_data: np.ndarray, i_data: np.ndarray) -> str:
    """
    Analyze SANS data to create a description for AI model suggestion.

    Args:
        q_data: Q values (scattering vector)
        i_data: Intensity values

    Returns:
        String description of the data characteristics
    """
    # Calculate key features
    log_i = np.log10(i_data + 1e-10)  # Avoid log(0)
    log_q = np.log10(q_data + 1e-10)

    # Slope in log-log space (power law exponent)
    slope = np.polyfit(log_q, log_i, 1)[0]

    # Intensity ratio (high Q to low Q)
    low_q_intensity = np.mean(i_data[: len(i_data) // 10])
    high_q_intensity = np.mean(i_data[-len(i_data) // 10 :])
    intensity_ratio = low_q_intensity / (high_q_intensity + 1e-10)

    # Q range
    q_min, q_max = q_data.min(), q_data.max()

    description = f"""Data Analysis:
- Q range: {q_min:.4f} to {q_max:.4f} Å⁻¹
- Power law slope: {slope:.2f}
- Intensity decay: {intensity_ratio:.1f}x from low to high Q
- Data points: {len(q_data)}
"""
    return description


def suggest_models_simple(q_data: np.ndarray, i_data: np.ndarray) -> list[str]:
    """
    Simple heuristic-based model suggestion.

    This is a placeholder for AI-based suggestion. Based on data characteristics,
    suggests appropriate SANS models.

    Args:
        q_data: Q values
        i_data: Intensity values

    Returns:
        List of suggested model names
    """
    log_i = np.log10(i_data + 1e-10)
    log_q = np.log10(q_data + 1e-10)

    # Calculate slope
    slope = np.polyfit(log_q, log_i, 1)[0]

    suggestions = []

    # Heuristic rules based on slope and shape
    if slope < -3.5:
        # Steep decay - likely spherical particles
        suggestions = ['sphere', 'core_shell_sphere', 'fuzzy_sphere']
    elif -3.5 <= slope < -2:
        # Moderate decay - could be cylindrical or ellipsoidal
        suggestions = ['cylinder', 'ellipsoid', 'core_shell_cylinder']
    elif -2 <= slope < -1:
        # Gentle decay - possibly flat structures or aggregates
        suggestions = ['parallelepiped', 'lamellar', 'flexible_cylinder']
    else:
        # Flat or increasing - unusual, suggest common models
        suggestions = ['sphere', 'cylinder', 'ellipsoid']

    return suggestions[:5]  # Return top 5 suggestions


# =============================================================================
# Plotting
# =============================================================================


def plot_data_and_fit(
    fitter: SANSFitter,
    show_fit: bool = False,
    fit_q: Optional[np.ndarray] = None,
    fit_i: Optional[np.ndarray] = None,
) -> go.Figure:
    """
    Create an interactive Plotly figure with data and optionally fitted curve.

    Args:
        fitter: SANSFitter instance with loaded data
        show_fit: Whether to show fitted curve
        fit_q: Q values for fitted curve
        fit_i: Intensity values for fitted curve (NaN entries are skipped)

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    # Plot original data with error bars
    fig.add_trace(
        go.Scatter(
            x=fitter.data.x,
            y=fitter.data.y,
            error_y={'type': 'data', 'array': fitter.data.dy, 'visible': True},
            mode='markers',
            name='Data',
            marker={'size': 6, 'color': 'blue', 'symbol': 'circle'},
        )
    )

    # Plot fitted curve if available
    if show_fit and fit_q is not None and fit_i is not None:
        fig.add_trace(
            go.Scatter(
                x=fit_q,
                y=fit_i,
                mode='lines',
                name='Fitted Model',
                line={'color': 'red', 'width': 2},
            )
        )

    # Update layout
    fig.update_layout(
        title='SANS Data Analysis',
        xaxis_title='Q (Å⁻¹)',
        yaxis_title='Intensity (cm⁻¹)',
        xaxis_type='log',
        yaxis_type='log',
        hovermode='closest',
        template='plotly_white',
        height=600,
        showlegend=True,
    )

    return fig


def calculate_residuals(
    experimental_i: np.ndarray,
    fitted_i: np.ndarray,
    uncertainties: np.ndarray,
) -> np.ndarray:
    """
    Calculate normalized (weighted) residuals.

    Args:
        experimental_i: Experimental intensity values
        fitted_i: Fitted model intensity values (NaN where a point was not fitted)
        uncertainties: Measurement uncertainties (dI)

    Returns:
        Normalized residuals: (I_exp - I_fit) / dI. NaN entries in ``fitted_i``
        (points outside the fit Q range) propagate as NaN residuals.
    """
    experimental_i = np.asarray(experimental_i, dtype=float)
    fitted_i = np.asarray(fitted_i, dtype=float)
    uncertainties = np.asarray(uncertainties, dtype=float)
    # Avoid division by zero
    safe_uncertainties = np.where(uncertainties > 0, uncertainties, 1e-10)
    return (experimental_i - fitted_i) / safe_uncertainties


def plot_data_fit_and_residuals(
    fitter: SANSFitter,
    fit_q: np.ndarray,
    fit_i: np.ndarray,
) -> go.Figure:
    """
    Create a combined figure with data/fit plot and residuals subplot.

    Args:
        fitter: SANSFitter instance with loaded data
        fit_q: Q values for fitted curve
        fit_i: Intensity values for fitted curve (NaN entries are skipped)

    Returns:
        Plotly figure with two subplots (main plot + residuals)
    """
    # Calculate residuals
    residuals = calculate_residuals(fitter.data.y, fit_i, fitter.data.dy)

    # Create subplots: main plot (larger) + residuals (smaller)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
    )

    # Main plot: Data with error bars
    fig.add_trace(
        go.Scatter(
            x=fitter.data.x,
            y=fitter.data.y,
            error_y={'type': 'data', 'array': fitter.data.dy, 'visible': True},
            mode='markers',
            name='Data',
            marker={'size': 6, 'color': 'blue', 'symbol': 'circle'},
        ),
        row=1,
        col=1,
    )

    # Main plot: Fitted curve
    fig.add_trace(
        go.Scatter(
            x=fit_q,
            y=fit_i,
            mode='lines',
            name='Fitted Model',
            line={'color': 'red', 'width': 2},
        ),
        row=1,
        col=1,
    )

    # Residuals plot: scatter points
    fig.add_trace(
        go.Scatter(
            x=fitter.data.x,
            y=residuals,
            mode='markers',
            name='Residuals',
            marker={'size': 5, 'color': 'green', 'symbol': 'circle'},
            showlegend=True,
        ),
        row=2,
        col=1,
    )

    # Residuals plot: zero reference line
    fig.add_trace(
        go.Scatter(
            x=[fitter.data.x.min(), fitter.data.x.max()],
            y=[0, 0],
            mode='lines',
            name='Zero',
            line={'color': 'gray', 'width': 1, 'dash': 'dash'},
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # Update layout
    fig.update_layout(
        title='SANS Data Analysis',
        hovermode='closest',
        template='plotly_white',
        height=750,  # Taller to accommodate both plots
        showlegend=True,
    )

    # Main plot axes (log-log)
    fig.update_xaxes(type='log', row=1, col=1)
    fig.update_yaxes(title_text='Intensity (cm⁻¹)', type='log', row=1, col=1)

    # Residuals axes (log-linear)
    fig.update_xaxes(title_text='Q (Å⁻¹)', type='log', row=2, col=1)
    fig.update_yaxes(title_text='(I_exp - I_fit) / dI', row=2, col=1)

    return fig
