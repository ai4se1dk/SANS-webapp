# Phase 3: Advanced Sync - Research

**Researched:** 2026-02-06
**Domain:** Streamlit session state synchronization for fit results, polydispersity, and structure factor MCP tools
**Confidence:** HIGH

## Summary

Phase 3 implements the "Advanced Sync" requirements (SYNC-04, SYNC-05, SYNC-06) that ensure `run-fit`, `enable-polydispersity`, and structure factor tools immediately update the Streamlit UI. The research analyzed the existing codebase architecture established in Phases 1-2, the current MCP tool implementations, and the UI components that need to receive synchronized state.

**Current State After Phase 2:**
- `SessionStateBridge` has all basic parameter widget setters working correctly
- MCP tools use bridge methods and set `needs_rerun` flag
- The sync flow is verified: Tool -> Bridge -> Session state -> needs_rerun -> UI rerun -> User sees changes
- 128 tests passing, including 16 sync flow integration tests

**The Gaps Identified:**

1. **SYNC-04 (run-fit)**: The `run_fit()` tool updates `fit_completed` and `fit_result` but does NOT:
   - Update parameter widget values with fitted results (the UI gets values from `fit_result['parameters']`)
   - Explicitly trigger a plot refresh (relies on `fit_completed` flag and UI rendering)
   - Bridge lacks methods for fit result state management beyond basic flags

2. **SYNC-05 (enable-polydispersity)**: The `enable_polydispersity()` tool:
   - Only sets `{param}_pd` value in fitter params (line 380)
   - Does NOT update `pd_enabled` session state flag
   - Does NOT update PD widget session state keys (`pd_width_{param}`, `pd_type_{param}`, `pd_n_{param}`, `pd_vary_{param}`)
   - Bridge lacks methods for PD widget state

3. **SYNC-06 (structure factor tools)**: The `set_structure_factor()` and `remove_structure_factor()` tools:
   - Only call fitter methods and set `needs_rerun`
   - Structure factor adds new parameters but bridge doesn't sync them to widgets
   - No UI indication of active structure factor
   - Bridge lacks structure factor state management

**Primary recommendation:** Extend SessionStateBridge with methods for fit result, polydispersity, and structure factor state. Refactor the three advanced tools to use these methods for full widget synchronization.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Streamlit | 1.40+ | Web app framework | Already in use, provides session_state API |
| FastMCP | 2.3+ | MCP server implementation | Already in use for tool definitions |
| sasmodels | latest | SANS model library | Provides polydispersity and structure factor APIs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.0+ | Testing framework | For sync verification tests |
| numpy | latest | Array operations | Fit result data handling |
| pandas | latest | Data frames | Fit results display |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Bridge methods for PD state | Direct session_state in tools | Bridge pattern established in Phase 1, maintains consistency |
| Individual PD setters | Single bulk PD setter | Individual setters allow partial updates |

## Architecture Patterns

### Current Project Structure (Relevant Files)
```
src/sans_webapp/
├── services/
│   ├── mcp_state_bridge.py    # Bridge - EXTEND for PD and SF state
│   └── ai_chat.py             # Chat handling, rerun check
├── mcp_server.py              # MCP tools - REFACTOR run_fit, enable_polydispersity, structure factor
├── components/
│   ├── parameters.py          # Polydispersity tab rendering (lines 238-433)
│   └── fit_results.py         # Fit results display (lines 41-296)
└── app.py                     # Main app, fit_completed check (line 324)
```

### Pattern 1: MCP Tool to UI Sync Flow (Established)
**What:** Complete flow from tool execution to UI update
**When to use:** Every state-modifying MCP tool
**Flow (verified in Phase 2):**
```
1. User sends chat message
2. Claude calls MCP tool (e.g., run-fit)
3. Tool executes operation on fitter
4. Tool calls bridge methods to update session state widgets
5. Tool calls bridge.set_needs_rerun(True)
6. Tool returns success message
7. Chat response completes
8. UI checks needs_rerun flag
9. UI clears flag and calls st.rerun()
10. Script reruns from top
11. Widgets/displays read from session_state during render
12. User sees updated values
```

### Pattern 2: Fit Result Sync Pattern
**What:** After fit completes, update both status flags and parameter values
**When to use:** run-fit tool
**Current flow:**
```python
# Source: mcp_server.py lines 468-475 (current - incomplete)
bridge.set_fit_completed(True)
bridge.set_fit_result(result)
bridge.set_needs_rerun(True)
```
**Required flow:**
```python
# After fit completes:
1. Set fit_completed = True
2. Set fit_result = result (for chi-squared display)
3. Update parameter widget values from fitted params
4. Set needs_rerun = True
```

### Pattern 3: Polydispersity Widget Key Convention
**What:** PD widgets use consistent key naming in parameters.py
**Keys (from parameters.py lines 266-269):**
```python
pd_width_key = f'pd_width_{param_name}'   # e.g., 'pd_width_radius'
pd_n_key = f'pd_n_{param_name}'           # e.g., 'pd_n_radius'
pd_type_key = f'pd_type_{param_name}'     # e.g., 'pd_type_radius'
pd_vary_key = f'pd_vary_{param_name}'     # e.g., 'pd_vary_radius'
```
**Master toggle (line 386-387):**
```python
pd_enabled_key = 'pd_enabled'             # Master enable flag
```

### Pattern 4: Structure Factor State Pattern
**What:** Structure factor adds parameters that need widget sync
**When to use:** set-structure-factor, remove-structure-factor tools
**Flow:**
```
1. Call fitter.set_structure_factor(sf_name)
2. New structure factor parameters appear in fitter.params
3. Clear old parameter widgets (model changed)
4. Initialize new parameter widgets including SF params
5. Set indicator state for UI (optional: sf_name or None)
```

### Anti-Patterns to Avoid
- **Setting widget state without clearing old state:** Causes value carryover between different model configurations
- **Forgetting pd_enabled master toggle:** PD widgets won't render even if individual params set
- **Not syncing fit result to parameter widgets:** Users see chi-squared but not updated values
- **Calling st.rerun() in tools:** Breaks execution flow (use needs_rerun flag)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PD widget state | Direct session_state in tools | Bridge PD setter methods | Centralized, consistent with Phase 1 pattern |
| Fit result parameter sync | Manual loop in tool | Bridge method with fitter param access | Complex logic (varies flag, stderr handling) |
| SF parameter initialization | Manual key setting | clear_parameter_widgets() + let UI initialize | UI already handles initialization from fitter |
| Value clamping | Raw value assignment | clamp_for_display() | Handles inf, large numbers, precision |

**Key insight:** Extend the bridge pattern established in Phase 1. All advanced state sync should go through SessionStateBridge methods.

## Common Pitfalls

### Pitfall 1: Fit Results Not Reflected in Parameter Widgets
**What goes wrong:** After fit, chi-squared displays but parameter value widgets still show pre-fit values
**Why it happens:** `run_fit()` updates `fit_result` but doesn't sync to `value_{param}` widget keys
**How to avoid:** After successful fit, iterate fitted parameters and call `set_parameter_value()` for each
**Warning signs:** Parameter table shows old values, fit result table shows new values
**Code location:** mcp_server.py `run_fit()` function

### Pitfall 2: Polydispersity Master Toggle Not Set
**What goes wrong:** PD parameter widgets have correct values but PD tab shows "disabled"
**Why it happens:** `enable_polydispersity()` tool sets individual PD params but not `pd_enabled` flag
**How to avoid:** Always set `st.session_state.pd_enabled = True` when enabling PD
**Warning signs:** PD tab says "Enable polydispersity to configure" despite tool success
**Code location:** mcp_server.py `enable_polydispersity()` function

### Pitfall 3: PD Widget Keys vs Fitter PD API Mismatch
**What goes wrong:** PD values set but widgets show different values
**Why it happens:** Fitter uses `pd`, UI uses `pd_width`; fitter returns dict, UI expects individual keys
**How to avoid:** Bridge methods translate between fitter API and UI widget keys:
  - `fitter.set_pd_param(param, pd_width=X)` sets fitter
  - `bridge.set_pd_widget(param, pd_width=X)` sets `st.session_state[f'pd_width_{param}']`
**Warning signs:** Values don't match between fitter and UI
**Code reference:** parameters.py PDUpdate TypedDict uses `pd_width`, fitter uses `pd`

### Pitfall 4: Structure Factor Parameters Not Displayed
**What goes wrong:** Structure factor added successfully but no SF parameter widgets appear
**Why it happens:** Parameter widgets initialized before SF added; needs full widget refresh
**How to avoid:** Call `clear_parameter_widgets()` and `set_needs_rerun()` after SF change
**Warning signs:** Tool says "Structure factor added" but parameter table unchanged
**Current behavior:** Tools already call `set_needs_rerun()`, but widgets may not reinitialize

### Pitfall 5: Plot Not Refreshing After Fit
**What goes wrong:** Fit completes, chi-squared shows, but plot still shows pre-fit curve
**Why it happens:** Plot renders based on fitter state, should update on rerun
**How to avoid:** Ensure `fit_completed = True` is set BEFORE `needs_rerun`
**Warning signs:** Stale plot after successful fit
**Verification:** fit_results.py line 54-68 re-calculates fit_i on each render

## Code Examples

Verified patterns from the existing codebase:

### Current run_fit Tool Implementation (Needs Extension)
```python
# Source: mcp_server.py lines 448-495
def run_fit() -> str:
    # ... validation ...
    result = fitter.fit()

    # Current sync (INCOMPLETE):
    bridge = get_state_bridge()
    bridge.set_fit_completed(True)
    bridge.set_fit_result(result)
    bridge.set_needs_rerun(True)

    # MISSING: Sync fitted parameter values to widgets
    # Should add:
    # for name, param in fitter.params.items():
    #     if getattr(param, 'vary', False):
    #         bridge.set_parameter_value(name, param.value)
```

### Current enable_polydispersity Tool Implementation (Needs Extension)
```python
# Source: mcp_server.py lines 358-390
def enable_polydispersity(
    parameter_name: str, pd_type: str = 'gaussian', pd_value: float = 0.1
) -> str:
    # ... validation ...

    # Current sync (INCOMPLETE):
    pd_param_name = f'{parameter_name}_pd'
    if hasattr(fitter, 'params') and pd_param_name in fitter.params:
        fitter.params[pd_param_name].value = pd_value
        fitter.params[pd_param_name].vary = True
        bridge.set_needs_rerun(True)

    # MISSING:
    # - Set st.session_state.pd_enabled = True
    # - Set pd_width_{param}, pd_type_{param}, pd_n_{param}, pd_vary_{param}
```

### PD Widget Initialization Pattern (From UI)
```python
# Source: components/parameters.py lines 266-279
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
```

### Fit Results Display Pattern (For Reference)
```python
# Source: components/fit_results.py lines 80-97
def _render_fit_statistics(fitter: SANSFitter) -> None:
    """Render chi-squared and residual statistics."""
    if 'fit_result' in st.session_state and 'chisq' in st.session_state.fit_result:
        chi_squared = cast(FitResult, st.session_state.fit_result).get('chisq')
        if chi_squared is not None:
            st.markdown(f'{CHI_SQUARED_LABEL}{chi_squared:.4f}')
            # ... residual calculations
```

### Required New Bridge Methods
```python
# Pattern for new methods to add to SessionStateBridge

# PD state management
def set_pd_enabled(self, enabled: bool) -> None:
    """Set the master polydispersity enable flag."""
    st.session_state.pd_enabled = enabled

def set_pd_widget(
    self,
    param_name: str,
    pd_width: float | None = None,
    pd_n: int | None = None,
    pd_type: str | None = None,
    vary: bool | None = None,
) -> None:
    """Set polydispersity widget state for a parameter."""
    if pd_width is not None:
        st.session_state[f'pd_width_{param_name}'] = float(pd_width)
    if pd_n is not None:
        st.session_state[f'pd_n_{param_name}'] = int(pd_n)
    if pd_type is not None:
        st.session_state[f'pd_type_{param_name}'] = pd_type
    if vary is not None:
        st.session_state[f'pd_vary_{param_name}'] = vary

def clear_pd_widgets(self) -> None:
    """Clear all PD widget state (for model changes)."""
    keys_to_remove = [
        k for k in st.session_state.keys()
        if k.startswith('pd_width_')
        or k.startswith('pd_n_')
        or k.startswith('pd_type_')
        or k.startswith('pd_vary_')
    ]
    for key in keys_to_remove:
        del st.session_state[key]

# Structure factor state (optional - may not need dedicated state)
def set_structure_factor_name(self, sf_name: str | None) -> None:
    """Set the active structure factor name (None if removed)."""
    st.session_state.structure_factor = sf_name
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual fit result display | Session state fit_result dict | Phase 1 | Centralized fit data |
| Direct PD fitter calls | Bridge + session state sync | Phase 3 (planned) | UI auto-updates |
| No SF state tracking | Bridge SF state methods | Phase 3 (planned) | User sees active SF |

**Already implemented (Phases 1-2):**
- Basic parameter widget setters in SessionStateBridge
- needs_rerun flag pattern for all state-modifying tools
- Fit result and fit_completed flags in bridge

**Needed for Phase 3:**
- PD widget setters in bridge
- Update run_fit to sync fitted values to parameter widgets
- Update enable_polydispersity to sync PD widget state
- Update structure factor tools to clear/reinitialize widgets

## Open Questions

Things that require verification during implementation:

1. **Fitted PD Parameters in run_fit**
   - What we know: When PD is enabled and varied, fit results include `{param}_pd` values
   - What's unclear: Should run_fit sync these to pd_width_{param} session state?
   - Recommendation: Yes, sync PD fitted values alongside regular params

2. **Structure Factor Widget Reinitialization**
   - What we know: Adding SF adds new parameters to fitter.params
   - What's unclear: Does clear_parameter_widgets() + rerun properly initialize new params?
   - Recommendation: Verify this works; if not, may need explicit initialization

3. **Multiple PD Parameters**
   - What we know: Models can have multiple polydisperse parameters (e.g., sphere has radius)
   - What's unclear: Should enable_polydispersity set ALL available PD params or just the one specified?
   - Recommendation: Only set the specified parameter; user can enable multiple via separate calls

4. **pd_updates Session State Sync**
   - What we know: UI stores pd_updates dict in session state for form submission
   - What's unclear: Should bridge update pd_updates dict or just individual widget keys?
   - Recommendation: Update individual widget keys; pd_updates is rebuilt from widgets on form submit

## Verification Requirements

### SYNC-04 Verification: run-fit Tool
Test: When Claude calls `run-fit`:
- [ ] `st.session_state.fit_completed` == True
- [ ] `st.session_state.fit_result` contains chi-squared and parameters
- [ ] For each varied parameter: `st.session_state[f'value_{name}']` == fitted value
- [ ] Plot shows fitted curve (visual verification)
- [ ] Chi-squared value displays in fit results section

### SYNC-05 Verification: enable-polydispersity Tool
Test: When Claude calls `enable-polydispersity "radius"`:
- [ ] `st.session_state.pd_enabled` == True
- [ ] `st.session_state['pd_width_radius']` == specified pd_value
- [ ] `st.session_state['pd_type_radius']` == specified pd_type
- [ ] `st.session_state['pd_vary_radius']` == True
- [ ] PD tab shows enabled state with correct values

### SYNC-06 Verification: Structure Factor Tools
Test: When Claude calls `set-structure-factor "hardsphere"`:
- [ ] Fitter has structure factor applied (fitter.structure_factor is set)
- [ ] `st.session_state.needs_rerun` was set (triggers refresh)
- [ ] Parameter table includes structure factor parameters after rerun

Test: When Claude calls `remove-structure-factor`:
- [ ] Fitter structure factor removed
- [ ] Parameter table no longer shows SF parameters

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `mcp_state_bridge.py`, `mcp_server.py`, `parameters.py`, `fit_results.py`, `app.py`
- Phase 1 and Phase 2 Research and Summary documents
- [Streamlit Session State Docs](https://docs.streamlit.io/develop/concepts/architecture/session-state) - Widget key patterns, execution model
- [Streamlit Widget Updating](https://docs.streamlit.io/knowledge-base/using-streamlit/widget-updating-session-state) - Proper update patterns

### Secondary (MEDIUM confidence)
- [Streamlit 2026 Release Notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) - Latest widget behavior

### Tertiary (LOW confidence)
- sasmodels polydispersity API (verify exact method signatures with fitter)
- sasmodels structure factor API (verify exact method signatures with fitter)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing libraries in codebase
- Architecture: HIGH - Extending patterns established in Phases 1-2
- Pitfalls: HIGH - Identified from codebase analysis and Phase 1-2 learnings

**Research date:** 2026-02-06
**Valid until:** 30 days (stable implementation, extending established patterns)

---

## Implementation Guidance

Based on research, Phase 3 should focus on:

### 1. Extend SessionStateBridge (INFRA-like work)

Add methods for:
- PD state: `set_pd_enabled()`, `set_pd_widget()`, `clear_pd_widgets()`
- Optional: `set_structure_factor_name()` for UI indication

### 2. Refactor run_fit Tool (SYNC-04)

After successful fit:
1. Call existing `bridge.set_fit_completed(True)`
2. Call existing `bridge.set_fit_result(result)`
3. **NEW**: Loop through fitter.params and call `bridge.set_parameter_value()` for varied params
4. **NEW**: If PD enabled and PD params varied, sync PD widget values
5. Call existing `bridge.set_needs_rerun(True)`

### 3. Refactor enable_polydispersity Tool (SYNC-05)

After enabling PD for a parameter:
1. Set fitter PD values (existing)
2. **NEW**: Call `bridge.set_pd_enabled(True)`
3. **NEW**: Call `bridge.set_pd_widget(param, pd_width=..., pd_type=..., vary=True)`
4. Call existing `bridge.set_needs_rerun(True)`

### 4. Refactor Structure Factor Tools (SYNC-06)

For set_structure_factor:
1. Call `fitter.set_structure_factor(sf_name)` (existing)
2. **NEW**: Call `bridge.clear_parameter_widgets()` (new params need fresh init)
3. Call existing `bridge.set_needs_rerun(True)`

For remove_structure_factor:
1. Call `fitter.remove_structure_factor()` (existing)
2. **NEW**: Call `bridge.clear_parameter_widgets()` (SF params removed)
3. Call existing `bridge.set_needs_rerun(True)`

### 5. Integration Tests

Create tests similar to Phase 2 pattern:
- TestSyncRunFit class for SYNC-04
- TestSyncPolydispersity class for SYNC-05
- TestSyncStructureFactor class for SYNC-06

### Success Criteria Mapping

| Requirement | Bridge Methods Needed | Tool Refactoring |
|-------------|----------------------|------------------|
| SYNC-04 | (existing param setters) | run_fit: sync fitted values |
| SYNC-05 | set_pd_enabled, set_pd_widget, clear_pd_widgets | enable_polydispersity: full PD sync |
| SYNC-06 | (uses existing clear_parameter_widgets) | structure factor tools: clear widgets |
