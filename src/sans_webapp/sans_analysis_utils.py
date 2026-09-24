"""
SANS Data Analysis Utility Functions

Shared utility functions for SANS data analysis that can be used by both
the Streamlit web application and command-line scripts without importing Streamlit.
"""

import logging
import threading
import warnings
from contextlib import contextmanager
from typing import Any, Optional

import numpy as np
import plotly.graph_objects as go
from sans_fitter import SANSFitter, get_all_models
from sans_fitter.console import LOGGER_NAME
from sans_fitter.data.loader import has_real_data
from sans_fitter.plotting import plot_fit

CURRENT_PARAMETERS_LABEL = 'Current parameters'

# Re-export get_all_models for backwards compatibility
__all__ = [
    'get_all_models',
    'analyze_data_for_ai_suggestion',
    'suggest_models_simple',
    'plot_data',
    'plot_fit_results',
    'fit_is_current',
    'plot_model_preview',
    'snapshot_parameters',
    'plot_parameter_comparison',
    'calculate_residuals',
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


# =============================================================================
# Plotting (delegated to sans-fitter's figure builders)
# =============================================================================


@contextmanager
def _quiet_fitter():
    """Silence sans-fitter's progress logging for the duration of the block.

    Streamlit reruns the script on every interaction, and the preview/plot
    builders log a status line each time they are called.

    Streamlit runs each browser session in its own thread, so this filters
    only the calling thread's records below ERROR rather than changing the
    shared logger's level, which concurrent sessions could leave raised.
    The plotting and preview code logs through the ``sans_fitter`` logger
    itself, where the filter applies.
    """
    logger = logging.getLogger(LOGGER_NAME)
    thread_id = threading.get_ident()

    def drop_own_progress(record: logging.LogRecord) -> bool:
        return record.thread != thread_id or record.levelno >= logging.ERROR

    logger.addFilter(drop_own_progress)
    try:
        yield
    finally:
        logger.removeFilter(drop_own_progress)


def _fit_container(fig: go.Figure) -> go.Figure:
    """Let a sans-fitter figure size itself to its Streamlit container."""
    fig.update_layout(width=None, autosize=True)
    return fig


def plot_data(fitter: SANSFitter, log_scale: bool = True) -> go.Figure:
    """
    Plot the loaded data only (I(Q) with dI and, when present, dQ error bars).

    Args:
        fitter: SANSFitter instance with loaded data
        log_scale: Use log scale on both axes

    Returns:
        Plotly figure object
    """
    with _quiet_fitter():
        fig = plot_fit(
            fitter.data,
            None,
            fitter.model_name,
            show_residuals=False,
            log_scale=log_scale,
            show=False,
        )
    return _fit_container(fig)


def fit_is_current(fitter: SANSFitter) -> bool:
    """
    Whether the fitter's last fit still describes its current configuration.

    False once a parameter value, bound, vary flag, link, polydispersity
    setting, the resolution mode, the fitting Q range or the data changed
    after the fit, i.e. whenever the stored fitted curve no longer matches
    what the model gives at the current settings.

    Args:
        fitter: SANSFitter instance

    Returns:
        True if a fit exists and nothing it depends on has changed since
    """
    if getattr(fitter, 'fit_result', None) is None:
        return False
    # sans-fitter records the configuration each fit belongs to (the same
    # check save_analysis() uses to flag stale results). There is no public
    # accessor for it yet, so read it defensively.
    contract = getattr(fitter, '_fit_contract', None)
    saved_context = getattr(contract, 'fit_context', None)
    if saved_context is None:
        return False
    try:
        from sans_fitter.persistence import _current_fit_context, compare_fit_context

        current = _current_fit_context(fitter, fitter._param_manager.export_config())
        return compare_fit_context(saved_context, current) is None
    except Exception:
        # The private API changed or failed: fall back to the model preview
        return False


def plot_fit_results(
    fitter: SANSFitter, show_residuals: bool = True, log_scale: bool = True
) -> go.Figure:
    """
    Plot the data against the model, with optional residual panel.

    Shows the last fit (``SANSFitter.plot_results``) while it still describes
    the fitter's settings, and the model at the current parameters
    (``SANSFitter.plot_model``) once anything changed after the fit, e.g. a
    parameter adjusted with the slider. Either way the figure marks points
    outside the fitting Q range, draws dQ error bars when the data has them,
    reports chi-squared/dof in the title and leaves the residual panel empty
    rather than dividing by zero when the data has no dI.

    Args:
        fitter: SANSFitter instance with data and a model loaded
        show_residuals: Add a residuals panel below the main plot
        log_scale: Use log scale on both axes

    Returns:
        Plotly figure object
    """
    with _quiet_fitter():
        if fit_is_current(fitter):
            fig = fitter.plot_results(
                show_residuals=show_residuals, log_scale=log_scale, show=False
            )
        else:
            fig = fitter.plot_model(show_residuals=show_residuals, log_scale=log_scale, show=False)
    return _fit_container(fig)


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
        Normalized residuals: (I_exp - I_fit) / dI. NaN where a point was not
        fitted (NaN in ``fitted_i``) and where dI is not positive, since a
        residual in sigma units is undefined without an uncertainty.
    """
    experimental_i = np.asarray(experimental_i, dtype=float)
    fitted_i = np.asarray(fitted_i, dtype=float)
    uncertainties = np.asarray(uncertainties, dtype=float)
    with np.errstate(divide='ignore', invalid='ignore'):
        residuals = (experimental_i - fitted_i) / uncertainties
    return np.where(uncertainties > 0, residuals, np.nan)


def plot_model_preview(
    fitter: SANSFitter, show_residuals: bool = True, log_scale: bool = True
) -> go.Figure:
    """
    Plot the data against the model at the current parameters, without fitting.

    Uses ``SANSFitter.plot_model()``: the curve is evaluated exactly as a fit
    would evaluate it (polydispersity, links, structure factor, resolution) and
    the title reports chi-squared/dof at the current values, so starting values
    can be judged before running a fit.

    Args:
        fitter: SANSFitter instance with data and a model loaded
        show_residuals: Add a residuals panel below the main plot
        log_scale: Use log scale on both axes

    Returns:
        Plotly figure object
    """
    with _quiet_fitter():
        fig = fitter.plot_model(show_residuals=show_residuals, log_scale=log_scale, show=False)
    return _fit_container(fig)


def snapshot_parameters(fitter: SANSFitter) -> dict[str, float]:
    """
    Capture the current parameter values as overrides for ``SANSFitter.compare()``.

    Linked parameters are left out (they follow their leader), and
    polydispersity widths are included as ``<name>_pd`` while polydispersity
    is enabled.

    Args:
        fitter: SANSFitter instance with a model loaded

    Returns:
        Parameter name -> value
    """
    followers = set(fitter.get_links())
    values = {
        name: float(info['value']) for name, info in fitter.params.items() if name not in followers
    }
    if fitter.supports_polydispersity() and fitter.is_polydispersity_enabled():
        for name in fitter.get_polydisperse_parameters():
            values[f'{name}_pd'] = float(fitter.get_pd_param(name)['pd'])
    return values


def plot_parameter_comparison(
    fitter: SANSFitter,
    snapshots: dict[str, dict[str, float]],
    include_current: bool = True,
    log_scale: bool = True,
) -> go.Figure:
    """
    Overlay the model for several saved parameter sets over the data.

    Delegates to ``SANSFitter.compare()``, which evaluates each set without
    touching the fitter's own parameters.

    Args:
        fitter: SANSFitter instance with data and a model loaded
        snapshots: Label -> parameter values, as from ``snapshot_parameters()``
        include_current: Also draw the model at the current parameters
        log_scale: Use log scale on both axes

    Returns:
        Plotly figure object

    Raises:
        ValueError: If there is nothing to compare
    """
    cases: dict[str, dict[str, float]] = {}
    if include_current:
        cases[CURRENT_PARAMETERS_LABEL] = {}
    cases.update(snapshots)
    with _quiet_fitter():
        fig = fitter.compare(cases=cases, log_scale=log_scale, show=False)
    return _fit_container(fig)
