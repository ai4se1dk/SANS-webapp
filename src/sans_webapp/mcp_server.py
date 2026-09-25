"""
MCP Server for SANS-webapp AI Assistant.

Provides FastMCP-based tools for AI-assisted SANS model fitting.
Tools allow Claude to interact with SANSFitter: list models,
set parameters, restrict the fit Q range, run fits, and query results.

Targets sans-fitter >= 0.4: fit results are dictionaries with
``reduced_chisq`` / ``chisq`` / ``on_bounds`` / ``converged``, polydispersity
is configured through ``set_pd_param`` (not through ``params``), and the
fitted curve is obtained from ``SANSFitter.calculate()``.
"""

from typing import Any

import numpy as np
from sans_fitter import SANSFitter, get_all_models, get_structure_factors

from sans_webapp.sans_analysis_utils import (
    describe_fitter_state,
    format_fit_parameters,
    format_fit_summary,
    run_fit_with_warnings,
)

# Try to instantiate FastMCP, but be resilient in test environments where
# FastMCP's pydantic-based Settings may raise due to version mismatches.
try:
    from fastmcp import FastMCP

    mcp: Any = FastMCP(
        name='sans-webapp-mcp',
        instructions="""
You are a SANS (Small-Angle Neutron Scattering) data analysis assistant.
You help users fit scattering data to physical models using the sasmodels library.

Available capabilities:
- List available SANS models (sphere, cylinder, ellipsoid, etc.)
- Get detailed parameter information for any model
- Set the active model for fitting
- Adjust parameter values, bounds, and whether they vary during fitting
- Restrict the Q range used for fitting
- Enable polydispersity for size parameters
- Add/remove structure factors for interparticle interactions
- Run curve fitting optimization
- Retrieve fit results and statistics

When helping users:
1. Start by understanding their sample (shape, composition)
2. Suggest appropriate models based on sample description
3. Guide parameter setup with physically reasonable values
4. Run fits and interpret results
5. Suggest refinements if fit quality is poor

Always explain what you're doing and why. Use proper scientific units.
""",
    )
except Exception as e:  # pragma: no cover - environment-specific fallback
    # Create a lightweight dummy MCP with the minimal interface our code expects
    class _DummyMCP:
        def __init__(self):
            self._tools: dict[str, Any] = {}

        def tool(self, name: str):
            def decorator(fn):
                self._tools[name] = fn
                return fn

            return decorator

        def run(self):
            raise RuntimeError(
                'FastMCP is unavailable in this environment. Tools are not runnable.'
            )

    mcp: Any = _DummyMCP()
    _FASTMCP_IMPORT_ERROR = e

# Global reference to the fitter - set by webapp at startup
_fitter: SANSFitter | None = None


def set_fitter(fitter: SANSFitter) -> None:
    """Set the global fitter reference for MCP tools."""
    global _fitter
    _fitter = fitter


def get_fitter() -> SANSFitter:
    """Get the current fitter instance."""
    if _fitter is None:
        raise RuntimeError('Fitter not initialized. Load data first.')
    return _fitter


def _ensure_fitter_model_synced() -> None:
    """Re-load the model on the fitter if session state says one should be active.

    Between Streamlit reruns the fitter's ``kernel`` attribute can become ``None``
    while ``st.session_state`` still records which model was loaded.  This helper
    detects the mismatch and transparently re-applies ``set_model`` so that every
    tool sees the correct fitter state.

    After re-loading the model (which resets all params to defaults) we
    restore user-customised values from session-state widget keys
    (``value_<name>``, ``min_<name>``, ``max_<name>``, ``vary_<name>``).
    """
    try:
        import streamlit as st

        fitter = get_fitter()
        fitter_has_model = fitter.kernel is not None
        session_model = st.session_state.get('current_model', None)
        model_selected = st.session_state.get('model_selected', False)

        if not fitter_has_model and model_selected and session_model:
            fitter.set_model(session_model)
            _restore_params_from_session(fitter, st.session_state)
    except Exception:
        # Best-effort; never let sync failures break a tool call.
        pass


def _restore_params_from_session(fitter: SANSFitter, session_state: Any) -> None:
    """Restore parameter values from session-state widget keys after a model reload.

    Widget keys follow the pattern ``value_<name>``, ``min_<name>``,
    ``max_<name>``, ``vary_<name>``.  Only keys that are actually present
    in session state are applied, so default values are preserved for
    any parameter the user hasn't touched.
    """
    if not hasattr(fitter, 'params') or not fitter.params:
        return
    for name in fitter.params:
        kwargs: dict[str, Any] = {}
        val = session_state.get(f'value_{name}')
        if val is not None:
            kwargs['value'] = val
        min_val = session_state.get(f'min_{name}')
        if min_val is not None:
            kwargs['min'] = min_val
        max_val = session_state.get(f'max_{name}')
        if max_val is not None:
            kwargs['max'] = max_val
        vary_val = session_state.get(f'vary_{name}')
        if vary_val is not None:
            kwargs['vary'] = vary_val
        if kwargs:
            try:
                fitter.set_param(name, **kwargs)
            except Exception:
                pass


def _check_tools_enabled() -> bool:
    """Check if AI tools are enabled in session state."""
    from sans_webapp.services.mcp_state_bridge import get_state_bridge

    return get_state_bridge().are_tools_enabled()


def _supported_structure_factors() -> str:
    """Comma-separated structure factor names known to sasmodels (best effort)."""
    try:
        return ', '.join(get_structure_factors())
    except Exception:
        return 'hardsphere, hayter_msa, squarewell, stickyhardsphere'


# =============================================================================
# Read-only tools (no state mutation)
# =============================================================================


def list_sans_models() -> str:
    """
    List all available SANS models from sasmodels library.
    Returns a formatted list of model names that can be used with set-model.
    """
    models = get_all_models()
    return f'Available SANS models ({len(models)}):\n' + '\n'.join(
        f'  - {m}' for m in sorted(models)
    )


def get_model_parameters(model_name: str) -> str:
    """
    Get parameter details for a specific SANS model.
    Shows parameter names, default values, bounds, vary flags and which
    parameters support polydispersity.

    Args:
        model_name: Name of the model (e.g., 'sphere', 'cylinder')
    """
    try:
        # Create a temporary fitter to inspect model parameters
        temp_fitter = SANSFitter()
        temp_fitter.set_model(model_name)
        params = temp_fitter.params

        lines = [f"Parameters for '{model_name}':"]
        for name, param in params.items():
            value = param.get('value', 'N/A')
            p_min = param.get('min', None)
            p_max = param.get('max', None)
            vary = param.get('vary', True)
            lines.append(f'  - {name}: {value} (bounds: ({p_min}, {p_max}), vary: {vary})')

        try:
            if temp_fitter.supports_polydispersity():
                pd_names = temp_fitter.get_polydisperse_parameters()
                lines.append(f'Polydisperse parameters: {", ".join(pd_names)}')
        except Exception:
            pass

        return '\n'.join(lines)
    except Exception as e:
        return f"Error getting parameters for '{model_name}': {str(e)}"


def get_current_state() -> str:
    """
    Get the current state of the SANS fitter.
    Shows loaded data info (including the fit Q range and resolution mode),
    current model, structure factor, parameter values, polydispersity and
    the last fit summary.
    """
    try:
        _ensure_fitter_model_synced()
        fitter = get_fitter()

        lines = ['Current SANS Fitter State:']
        lines.extend(f'  {line}' for line in describe_fitter_state(fitter))
        return '\n'.join(lines)
    except Exception as e:
        return f'Error getting state: {str(e)}'


def get_fit_results() -> str:
    """
    Get the results from the most recent fit.
    Shows the reduced chi-squared, convergence, parameters resting on a bound,
    and the optimized parameter values with uncertainties.
    """
    try:
        _ensure_fitter_model_synced()
        fitter = get_fitter()

        fit_result = getattr(fitter, 'fit_result', None)
        if not isinstance(fit_result, dict) or not fit_result:
            return 'No fit results available. Run a fit first.'

        lines = ['Fit Results:']
        lines.extend(f'  {line}' for line in format_fit_summary(fit_result))

        varied = format_fit_parameters(fit_result)
        everything = format_fit_parameters(fit_result, include_fixed=True)
        fixed = [line for line in everything if line not in varied]

        lines.append('  Optimized parameters:')
        lines.extend(f'  {line}' for line in varied)
        if fixed:
            lines.append('  Fixed / linked parameters:')
            lines.extend(f'  {line}' for line in fixed)

        return '\n'.join(lines)
    except Exception as e:
        return f'Error getting fit results: {str(e)}'


# =============================================================================
# State-modifying tools (gated by ai_tools_enabled)
# =============================================================================


def set_model(model_name: str) -> str:
    """
    Load a SANS model for fitting.

    Args:
        model_name: Name of the model to load (e.g., 'sphere', 'cylinder', 'ellipsoid')
    """
    if not _check_tools_enabled():
        return 'AI tools are disabled. Enable them in the sidebar to allow model changes.'

    try:
        import streamlit as st

        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        _ensure_fitter_model_synced()
        fitter = get_fitter()

        # If the requested model is already loaded, skip the reload to
        # preserve any parameter customisations the user has made.
        # Check both the fitter object AND session state for robustness.
        current_model_name = fitter.model_name if fitter.kernel is not None else None
        session_model = st.session_state.get('current_model', None)
        if (current_model_name and current_model_name == model_name) or (
            session_model
            and session_model == model_name
            and st.session_state.get('model_selected', False)
        ):
            # Re-sync fitter if needed (session says model is loaded but fitter lost it)
            if not current_model_name:
                fitter.set_model(model_name)
            param_names = list(fitter.params.keys()) if hasattr(fitter, 'params') else []
            return (
                f"Model '{model_name}' is already loaded – keeping current parameter values.\n"
                f'Parameters: {", ".join(param_names)}'
            )

        fitter.set_model(model_name)

        # Update session state via bridge
        bridge = get_state_bridge()
        bridge.clear_parameter_widgets()  # Clear old model's widgets
        bridge.clear_pd_widgets()  # PD configuration belongs to the old model too
        bridge.set_current_model(model_name)
        bridge.set_model_selected(True)
        bridge.set_fit_completed(False)
        bridge.set_needs_rerun(True)

        param_names = list(fitter.params.keys()) if hasattr(fitter, 'params') else []
        return f"Model '{model_name}' loaded successfully.\nParameters: {', '.join(param_names)}"
    except Exception as e:
        return f"Error setting model '{model_name}': {str(e)}"


def set_parameter(
    name: str,
    value: float | None = None,
    min_bound: float | None = None,
    max_bound: float | None = None,
    vary: bool | None = None,
) -> str:
    """
    Set a parameter's value and/or fitting options.

    Args:
        name: Parameter name (e.g., 'radius', 'sld')
        value: New value for the parameter (optional)
        min_bound: Minimum bound for fitting (optional)
        max_bound: Maximum bound for fitting (optional)
        vary: Whether parameter should vary during fitting (optional)
    """
    if not _check_tools_enabled():
        return 'AI tools are disabled. Enable them in the sidebar to allow parameter changes.'

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        _ensure_fitter_model_synced()
        fitter = get_fitter()

        if not hasattr(fitter, 'params') or name not in fitter.params:
            return f"Parameter '{name}' not found. Available: {list(fitter.params.keys())}"

        changes = []

        # Use fitter.set_param() — the canonical API that correctly
        # updates the internal dict-of-dicts parameter store.
        kwargs: dict[str, Any] = {}
        if value is not None:
            kwargs['value'] = value
            changes.append(f'value={value}')
        if min_bound is not None:
            kwargs['min'] = min_bound
            changes.append(f'min={min_bound}')
        if max_bound is not None:
            kwargs['max'] = max_bound
            changes.append(f'max={max_bound}')
        if vary is not None:
            kwargs['vary'] = vary
            changes.append(f'vary={vary}')

        if kwargs:
            fitter.set_param(name, **kwargs)

        # Update UI widgets via bridge
        bridge = get_state_bridge()
        bridge.set_parameter_widget(
            name, value=value, min_val=min_bound, max_val=max_bound, vary=vary
        )
        bridge.set_needs_rerun(True)

        return f"Parameter '{name}' updated: {', '.join(changes)}"
    except Exception as e:
        return f"Error setting parameter '{name}': {str(e)}"


def set_multiple_parameters(parameters: dict[str, dict]) -> str:
    """
    Set multiple parameters at once.

    Args:
        parameters: Dictionary mapping parameter names to their settings.
                   Each value is a dict with optional keys: 'value', 'min', 'max', 'vary'
                   Example: {"radius": {"value": 50, "vary": True}, "sld": {"value": 1e-6}}
    """
    if not _check_tools_enabled():
        return 'AI tools are disabled. Enable them in the sidebar to allow parameter changes.'

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        _ensure_fitter_model_synced()
        fitter = get_fitter()
        bridge = get_state_bridge()
        results = []

        for name, settings in parameters.items():
            if name not in fitter.params:
                results.append(f'  - {name}: NOT FOUND')
                continue

            changes = []

            # Build kwargs for fitter.set_param()
            kwargs: dict[str, Any] = {}
            if 'value' in settings:
                kwargs['value'] = settings['value']
                changes.append(f'value={settings["value"]}')
            if 'min' in settings:
                kwargs['min'] = settings['min']
                changes.append(f'min={settings["min"]}')
            if 'max' in settings:
                kwargs['max'] = settings['max']
                changes.append(f'max={settings["max"]}')
            if 'vary' in settings:
                kwargs['vary'] = settings['vary']
                changes.append(f'vary={settings["vary"]}')

            if kwargs:
                fitter.set_param(name, **kwargs)

            # Update UI widget via bridge
            bridge.set_parameter_widget(
                name,
                value=settings.get('value'),
                min_val=settings.get('min'),
                max_val=settings.get('max'),
                vary=settings.get('vary'),
            )

            results.append(f'  - {name}: {", ".join(changes)}')

        bridge.set_needs_rerun(True)

        return 'Parameters updated:\n' + '\n'.join(results)
    except Exception as e:
        return f'Error setting parameters: {str(e)}'


def set_q_range(qmin: float | None = None, qmax: float | None = None) -> str:
    """
    Restrict the Q range used for fitting (sans-fitter >= 0.4).

    Data points outside [qmin, qmax] stay visible in the plots but are excluded
    from the fit. Call with no arguments to reset to the full data range.

    Args:
        qmin: Lower Q limit in Å⁻¹ (optional; full range lower limit when omitted)
        qmax: Upper Q limit in Å⁻¹ (optional; full range upper limit when omitted)
    """
    if not _check_tools_enabled():
        return 'AI tools are disabled. Enable them in the sidebar to allow Q range changes.'

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        fitter = get_fitter()
        if not hasattr(fitter, 'data') or fitter.data is None:
            return 'No data loaded. Load data before setting a Q range.'

        if qmin is None and qmax is None:
            fitter.reset_q_range()
            action = 'reset to the full data range'
        else:
            fitter.set_q_range(qmin=qmin, qmax=qmax)
            action = 'updated'

        lo, hi = fitter.get_q_range()
        x = np.asarray(fitter.data.x, dtype=float)
        n_in_range = int(np.sum((x >= lo) & (x <= hi)))

        bridge = get_state_bridge()
        bridge.set_q_range_widgets(lo, hi)
        bridge.set_needs_rerun(True)

        return (
            f'Fit Q range {action}: [{lo:.6g}, {hi:.6g}] Å⁻¹ '
            f'({n_in_range} of {len(x)} points in the fit). '
            'Re-run the fit for the new range to take effect.'
        )
    except Exception as e:
        return f'Error setting Q range: {str(e)}'


def set_resolution(mode: str, dq_over_q: float | None = None) -> str:
    """
    Set how instrument resolution smears the model (sans-fitter >= 0.4).

    Args:
        mode: 'data' (the file's dQ column; unsmeared if it has none),
            'none' (no smearing) or 'pinhole' (constant relative width)
        dq_over_q: Relative Gaussian 1-sigma width, required for 'pinhole'
    """
    if not _check_tools_enabled():
        return 'AI tools are disabled. Enable them in the sidebar to allow resolution changes.'

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        fitter = get_fitter()
        fitter.set_resolution(mode, dq_over_q=dq_over_q)
        get_state_bridge().set_needs_rerun(True)

        detail = f' with dQ/Q = {dq_over_q}' if mode == 'pinhole' else ''
        return f"Resolution set to '{mode}'{detail}. Re-run the fit for it to take effect."
    except Exception as e:
        return f'Error setting resolution: {str(e)}'


def enable_polydispersity(
    parameter_name: str, pd_type: str = 'gaussian', pd_value: float = 0.1
) -> str:
    """
    Enable polydispersity for a size parameter.

    Turns polydispersity on globally, configures the distribution for the
    given parameter and marks its width as a fit parameter. Syncs the PD
    widget state so the UI shows the polydispersity tab with correct values.

    Args:
        parameter_name: Name of the parameter to make polydisperse (e.g., 'radius')
        pd_type: Distribution type ('gaussian', 'lognormal', 'schulz', 'rectangle', 'boltzmann')
        pd_value: Width of the distribution (relative, typically 0.01-0.5)
    """
    if not _check_tools_enabled():
        return 'AI tools are disabled. Enable them in the sidebar to allow polydispersity changes.'

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        _ensure_fitter_model_synced()
        fitter = get_fitter()
        bridge = get_state_bridge()

        if fitter.kernel is None:
            return 'No model selected. Set a model before enabling polydispersity.'

        if not fitter.supports_polydispersity():
            return f"Model '{fitter.model_name}' has no polydisperse parameters."

        pd_params = fitter.get_polydisperse_parameters()
        if parameter_name not in pd_params:
            return (
                f"'{parameter_name}' is not a polydisperse parameter of "
                f"'{fitter.model_name}'. Available: {', '.join(pd_params)}"
            )

        # sans-fitter keeps polydispersity outside ``params``: configure it
        # through the dedicated API and let it validate pd_type.
        fitter.enable_polydispersity(True)
        fitter.set_pd_param(parameter_name, pd_width=pd_value, pd_type=pd_type, vary=True)
        pd_config = fitter.get_pd_param(parameter_name)

        # Sync PD widget state so the UI shows the polydispersity tab
        bridge.set_pd_enabled(True)
        bridge.set_pd_widget(
            parameter_name,
            pd_width=pd_value,
            pd_n=int(pd_config.get('pd_n', 35)),
            pd_type=pd_type,
            vary=True,
        )
        bridge.set_needs_rerun(True)

        return (
            f"Polydispersity enabled for '{parameter_name}': {pd_type} distribution, "
            f'width={pd_value} (the width will vary during the fit).'
        )
    except Exception as e:
        return f'Error enabling polydispersity: {str(e)}'


def set_structure_factor(sf_name: str) -> str:
    """
    Add a structure factor to account for interparticle interactions.

    Args:
        sf_name: Structure factor name (e.g., 'hardsphere', 'stickyhardsphere', 'squarewell')
    """
    if not _check_tools_enabled():
        return (
            'AI tools are disabled. Enable them in the sidebar to allow structure factor changes.'
        )

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        _ensure_fitter_model_synced()
        fitter = get_fitter()

        if fitter.kernel is None:
            return 'No model selected. Set a form factor model before adding a structure factor.'

        before = set(fitter.params.keys()) if hasattr(fitter, 'params') else set()
        fitter.set_structure_factor(sf_name)

        bridge = get_state_bridge()
        bridge.clear_parameter_widgets()  # Old params; SF adds new ones
        bridge.set_needs_rerun(True)

        after = list(fitter.params.keys()) if hasattr(fitter, 'params') else []
        new_params = [name for name in after if name not in before]
        detail = f' New parameters: {", ".join(new_params)}.' if new_params else ''
        return (
            f"Structure factor '{sf_name}' applied to '{fitter.model_name}'."
            f'{detail} Additional parameters are now available for the interaction potential.'
        )
    except Exception as e:
        return (
            f"Error setting structure factor '{sf_name}': {str(e)} "
            f'Supported structure factors: {_supported_structure_factors()}'
        )


def remove_structure_factor() -> str:
    """Remove any structure factor from the current model."""
    if not _check_tools_enabled():
        return (
            'AI tools are disabled. Enable them in the sidebar to allow structure factor changes.'
        )

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        _ensure_fitter_model_synced()
        fitter = get_fitter()

        fitter.remove_structure_factor()

        bridge = get_state_bridge()
        bridge.clear_parameter_widgets()  # SF params are gone
        bridge.set_needs_rerun(True)

        return 'Structure factor removed.'
    except Exception as e:
        return f'Error removing structure factor: {str(e)}'


def run_fit(engine: str = 'bumps', method: str | None = None) -> str:
    """
    Run the curve fitting optimization.
    Uses the currently loaded model and parameter settings to fit the data.
    Returns fit quality metrics (reduced chi-squared, convergence, parameters
    at a bound) and optimized parameter values.

    Args:
        engine: Fitting engine, 'bumps' (default) or 'lmfit'
        method: Optimizer name (engine default when omitted):
                bumps: 'amoeba', 'lm', 'newton', 'de'; lmfit: 'leastsq',
                'least_squares', 'differential_evolution'
    """
    if not _check_tools_enabled():
        return 'AI tools are disabled. Enable them in the sidebar to run fits.'

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        fitter = get_fitter()

        if not hasattr(fitter, 'data') or fitter.data is None:
            return 'No data loaded. Load data before running a fit.'

        _ensure_fitter_model_synced()
        if fitter.kernel is None:
            return 'No model selected. Set a model before running a fit.'

        # Run the fit, capturing sans-fitter's warnings (bounds, convergence, ...)
        result, fit_warnings = run_fit_with_warnings(fitter, engine=engine, method=method)

        # Update session state via bridge
        bridge = get_state_bridge()
        bridge.set_fit_completed(True)
        bridge.set_fit_result(result)
        bridge.set_fit_warnings(fit_warnings)

        # Sync fitted parameter values to widget state (SYNC-04). The result's
        # parameters block lists every parameter; only the varied ones moved.
        for name, info in result.get('parameters', {}).items():
            if info.get('fixed', False):
                continue
            fitted_value = info.get('value')
            if fitted_value is None:
                continue
            if name in fitter.params:
                bridge.set_parameter_value(name, float(fitted_value))
            elif name.endswith('_pd'):
                # Polydispersity width (e.g. radius_pd) lives in the PD widgets
                bridge.set_pd_widget(name[:-3], pd_width=float(fitted_value))

        bridge.set_needs_rerun(True)

        # Format results
        lines = ['Fit completed!']
        lines.extend(format_fit_summary(result))
        lines.append('Optimized parameters:')
        lines.extend(format_fit_parameters(result))
        if fit_warnings:
            lines.append('Warnings:')
            lines.extend(f'  - {message}' for message in fit_warnings)

        return '\n'.join(lines)
    except Exception as e:
        return f'Fit failed: {str(e)}'


# =============================================================================
# Tool registration
# =============================================================================

mcp.tool(name='list-sans-models')(list_sans_models)
mcp.tool(name='get-model-parameters')(get_model_parameters)
mcp.tool(name='get-current-state')(get_current_state)
mcp.tool(name='get-fit-results')(get_fit_results)
mcp.tool(name='set-model')(set_model)
mcp.tool(name='set-parameter')(set_parameter)
mcp.tool(name='set-multiple-parameters')(set_multiple_parameters)
mcp.tool(name='set-q-range')(set_q_range)
mcp.tool(name='set-resolution')(set_resolution)
mcp.tool(name='enable-polydispersity')(enable_polydispersity)
mcp.tool(name='set-structure-factor')(set_structure_factor)
mcp.tool(name='remove-structure-factor')(remove_structure_factor)
mcp.tool(name='run-fit')(run_fit)


# =============================================================================
# Server runner (for standalone testing)
# =============================================================================

if __name__ == '__main__':
    mcp.run()
