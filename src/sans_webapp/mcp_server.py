"""
MCP Server for SANS-webapp AI Assistant.

Provides FastMCP-based tools for AI-assisted SANS model fitting.
Tools allow Claude to interact with SANSFitter: list models,
set parameters, run fits, and query results.
"""

from typing import Any

from sans_fitter import SANSFitter, get_all_models

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
    Shows parameter names, default values, units, and descriptions.

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

        return '\n'.join(lines)
    except Exception as e:
        return f"Error getting parameters for '{model_name}': {str(e)}"


def get_current_state() -> str:
    """
    Get the current state of the SANS fitter.
    Shows loaded data info, current model, and parameter values.
    """
    try:
        _ensure_fitter_model_synced()
        fitter = get_fitter()

        lines = ['Current SANS Fitter State:']

        # Data info
        if hasattr(fitter, 'data') and fitter.data is not None:
            data = fitter.data
            lines.append(
                f'  Data: {len(data.x)} points, Q range [{data.x.min():.4f}, {data.x.max():.4f}]'
            )
        else:
            lines.append('  Data: Not loaded')

        # Model info
        if fitter.kernel is not None:
            lines.append(f'  Model: {fitter.model_name or "Unknown"}')

            # Parameters
            if hasattr(fitter, 'params') and fitter.params:
                lines.append('  Parameters:')
                for name, param in fitter.params.items():
                    value = param.get('value', 'N/A')
                    vary = param.get('vary', True)
                    lines.append(f'    - {name}: {value} (vary: {vary})')
        else:
            lines.append('  Model: Not selected')

        return '\n'.join(lines)
    except Exception as e:
        return f'Error getting state: {str(e)}'


def get_fit_results() -> str:
    """
    Get the results from the most recent fit.
    Shows optimized parameter values, uncertainties, and fit statistics.
    """
    try:
        _ensure_fitter_model_synced()
        fitter = get_fitter()

        if not hasattr(fitter, 'result') or fitter.result is None:
            return 'No fit results available. Run a fit first.'

        result = fitter.result
        lines = ['Fit Results:']

        # Chi-square if available
        if hasattr(result, 'redchi'):
            lines.append(f'  Reduced chi-square: {result.redchi:.4f}')

        # Parameter values
        if hasattr(fitter, 'params') and fitter.params:
            lines.append('  Optimized parameters:')
            for name, param in fitter.params.items():
                value = param.get('value', 'N/A')
                stderr = param.get('stderr', None)
                if stderr:
                    lines.append(f'    - {name}: {value:.4g} ± {stderr:.4g}')
                else:
                    lines.append(f'    - {name}: {value:.4g}')

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


def enable_polydispersity(
    parameter_name: str, pd_type: str = 'gaussian', pd_value: float = 0.1
) -> str:
    """
    Enable polydispersity for a size parameter.

    Enables PD on the fitter and syncs all PD widget state so the UI
    immediately shows the polydispersity tab with correct values.

    Args:
        parameter_name: Name of the parameter to make polydisperse (e.g., 'radius')
        pd_type: Distribution type ('gaussian', 'lognormal', 'schulz')
        pd_value: Width of the distribution (relative, typically 0.01-0.5)
    """
    if not _check_tools_enabled():
        return 'AI tools are disabled. Enable them in the sidebar to allow polydispersity changes.'

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        fitter = get_fitter()
        bridge = get_state_bridge()

        # Check if model supports polydispersity for this parameter
        pd_param_name = f'{parameter_name}_pd'
        if hasattr(fitter, 'params') and pd_param_name in fitter.params:
            fitter.set_param(pd_param_name, value=pd_value, vary=True)

            # Determine pd_n from fitter if available, else default to 35
            pd_n = 35
            pd_n_param = f'{parameter_name}_pd_n'
            if pd_n_param in fitter.params:
                pd_n = int(fitter.params[pd_n_param].get('value', 35))

            # Sync PD widget state so the UI shows the polydispersity tab
            bridge.set_pd_enabled(True)
            bridge.set_pd_widget(
                parameter_name,
                pd_width=pd_value,
                pd_n=pd_n,
                pd_type=pd_type,
                vary=True,
            )
            bridge.set_needs_rerun(True)

            return f"Polydispersity enabled for '{parameter_name}': {pd_type} distribution, width={pd_value}"
        else:
            return f"Polydispersity parameter '{pd_param_name}' not found. This model may not support PD for '{parameter_name}'."
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

        fitter = get_fitter()

        if hasattr(fitter, 'set_structure_factor'):
            bridge = get_state_bridge()
            bridge.clear_parameter_widgets()  # Clear old params; SF adds new ones
            fitter.set_structure_factor(sf_name)
            bridge.set_needs_rerun(True)

            return f"Structure factor '{sf_name}' added. Additional parameters are now available for the interaction potential."
        else:
            return 'Structure factor support not available in this fitter version.'
    except Exception as e:
        return f'Error setting structure factor: {str(e)}'


def remove_structure_factor() -> str:
    """Remove any structure factor from the current model."""
    if not _check_tools_enabled():
        return (
            'AI tools are disabled. Enable them in the sidebar to allow structure factor changes.'
        )

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        fitter = get_fitter()

        if hasattr(fitter, 'remove_structure_factor'):
            bridge = get_state_bridge()
            bridge.clear_parameter_widgets()  # Clear SF params before removal
            fitter.remove_structure_factor()
            bridge.set_needs_rerun(True)

            return 'Structure factor removed.'
        else:
            return 'Structure factor support not available in this fitter version.'
    except Exception as e:
        return f'Error removing structure factor: {str(e)}'


def run_fit() -> str:
    """
    Run the curve fitting optimization.
    Uses the currently loaded model and parameter settings to fit the data.
    Returns fit quality metrics and optimized parameter values.
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

        # Run the fit
        result = fitter.fit()

        # Update session state via bridge
        bridge = get_state_bridge()
        bridge.set_fit_completed(True)
        bridge.set_fit_result(result)

        # Sync fitted parameter values to widget state (SYNC-04)
        for name, param in fitter.params.items():
            if param.get('vary', False):
                fitted_value = param.get('value', 0)
                bridge.set_parameter_value(name, fitted_value)

                # If this is a PD parameter (e.g. radius_pd), sync to PD widget too
                if name.endswith('_pd'):
                    base_param = name[:-3]  # Remove '_pd' suffix
                    bridge.set_pd_widget(base_param, pd_width=fitted_value)

        bridge.set_needs_rerun(True)

        # Format results
        lines = ['Fit completed!']

        if hasattr(result, 'redchi'):
            lines.append(f'Reduced chi-square: {result.redchi:.4f}')

        lines.append('Optimized parameters:')
        for name, param in fitter.params.items():
            if param.get('vary', False):
                value = param.get('value', 'N/A')
                stderr = param.get('stderr', None)
                if stderr:
                    lines.append(f'  - {name}: {value:.4g} ± {stderr:.4g}')
                else:
                    lines.append(f'  - {name}: {value:.4g}')

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
mcp.tool(name='enable-polydispersity')(enable_polydispersity)
mcp.tool(name='set-structure-factor')(set_structure_factor)
mcp.tool(name='remove-structure-factor')(remove_structure_factor)
mcp.tool(name='run-fit')(run_fit)


# =============================================================================
# Server runner (for standalone testing)
# =============================================================================

if __name__ == '__main__':
    mcp.run()
