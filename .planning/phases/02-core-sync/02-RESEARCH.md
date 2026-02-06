# Phase 2: Core Sync - Research

**Researched:** 2026-02-05
**Domain:** Streamlit session state synchronization for MCP tool-driven UI updates
**Confidence:** HIGH

## Summary

Phase 2 implements the "Core Sync" requirements (SYNC-01, SYNC-02, SYNC-03) that ensure MCP tool calls immediately update the Streamlit UI. The research analyzed the existing codebase architecture completed in Phase 1 and Streamlit's session state patterns to identify the implementation requirements.

**Current State After Phase 1:**
- `SessionStateBridge` already has all required setter methods: `set_parameter_value()`, `set_parameter_bounds()`, `set_parameter_vary()`, `set_parameter_widget()`, `clear_parameter_widgets()`
- MCP tools (`set-model`, `set-parameter`, `set-multiple-parameters`) already call bridge methods to update widget state
- All state-modifying tools set `needs_rerun` flag via bridge
- The `render_ai_chat_sidebar()` function checks `needs_rerun` and calls `st.rerun()` after chat responses

**The Gap:** The infrastructure is in place, but verification is needed that the complete sync cycle works end-to-end. Specifically:
1. When `set-model` is called, does the model selector dropdown reflect the new model?
2. When parameter tools are called, do the number_input widgets show updated values?
3. Is there any race condition or timing issue between state updates and widget rendering?

**Primary recommendation:** Phase 2 should focus on verification and testing of the existing implementation, with targeted fixes for any identified gaps rather than architectural changes.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Streamlit | 1.40+ | Web app framework | Already in use, provides session_state and widget APIs |
| FastMCP | 2.3+ | MCP server implementation | Already in use for tool definitions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.0+ | Testing framework | For sync verification tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct state modification | Widget callbacks | Callbacks are for user-initiated changes; tools need direct state modification |
| Immediate st.rerun() in tools | needs_rerun flag | Flag pattern prevents incomplete tool execution |

## Architecture Patterns

### Current Project Structure (Relevant Files)
```
src/sans_webapp/
├── services/
│   ├── mcp_state_bridge.py    # Bridge with setter methods (Phase 1 complete)
│   └── ai_chat.py             # Chat handling, rerun check after response
├── mcp_server.py              # MCP tools using bridge methods (Phase 1 complete)
├── components/
│   ├── sidebar.py             # Model selector, rerun check (lines 309-312)
│   └── parameters.py          # Parameter widgets with session state keys
└── app.py                     # Main app orchestration
```

### Pattern 1: MCP Tool to UI Sync Flow
**What:** Complete flow from tool execution to UI update
**When to use:** Every state-modifying MCP tool
**Flow:**
```
1. User sends chat message
2. Claude calls MCP tool (e.g., set-parameter)
3. Tool updates fitter state (param.value = new_value)
4. Tool calls bridge.set_parameter_widget(name, value=...)
   -> Bridge sets st.session_state[f'value_{name}'] = clamped_value
5. Tool calls bridge.set_needs_rerun(True)
6. Tool returns success message
7. Chat response completes
8. UI checks needs_rerun flag (sidebar.py line 309)
9. UI clears flag and calls st.rerun()
10. Script reruns from top
11. Widgets read from session_state during render
12. User sees updated values
```

### Pattern 2: Widget Key Initialization
**What:** Widgets initialize from session_state if key exists, else use default
**When to use:** All parameter widgets in parameters.py
**Code pattern:**
```python
# Source: components/parameters.py lines 176-184
if value_key not in st.session_state:
    st.session_state[value_key] = clamp_for_display(float(param_info['value']))

value = st.number_input(
    PARAMETER_VALUE_LABEL,
    format='%g',
    key=value_key,  # Widget reads from session_state[value_key]
    label_visibility='collapsed',
)
```

### Pattern 3: Model Selector is Not Key-Bound
**What:** The model selectbox in sidebar.py does NOT use a session_state key
**Implication:** set-model tool cannot directly update the selectbox display
**Current code (sidebar.py lines 160-166):**
```python
selected_model = st.selectbox(
    MODEL_SELECT_LABEL,
    options=all_models,
    index=all_models.index('sphere') if 'sphere' in all_models else 0,
    help=MODEL_SELECT_HELP,
)
```
**Note:** The selectbox has no `key` parameter, so it doesn't sync with session_state.
However, the actual model loading happens when user clicks "Load Model" button.
When Claude calls `set-model`, it directly sets the fitter model and session_state flags,
so the parameter table updates correctly even if the dropdown doesn't reflect the change.

### Anti-Patterns to Avoid
- **Setting widget state after widget renders:** Causes StreamlitAPIException
- **Calling st.rerun() inside tool execution:** Halts tool, leaves state inconsistent
- **Forgetting to clear old widget state on model change:** Causes value carryover
- **Not clamping extreme values:** Streamlit number_input can't handle inf/-inf

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Widget state updates | Direct st.session_state access in tools | SessionStateBridge methods | Centralized, uses clamp_for_display() |
| UI refresh after tools | Manual st.rerun() in tools | needs_rerun flag pattern | Tools don't know when UI is ready |
| Clearing old parameters | Manual key deletion | bridge.clear_parameter_widgets() | Catches all prefixes (value_, min_, max_, vary_) |
| Value formatting | Raw value assignment | clamp_for_display() | Handles inf, large numbers, precision |

**Key insight:** Phase 1 already implemented all the infrastructure. Phase 2 is about verifying it works and fixing edge cases.

## Common Pitfalls

### Pitfall 1: Model Selector Doesn't Update Visually
**What goes wrong:** After Claude calls `set-model`, the dropdown still shows the previous selection
**Why it happens:** The model selectbox has no `key` parameter bound to session_state
**How to avoid:** This is acceptable behavior because:
  1. The fitter.model is updated correctly
  2. st.session_state.current_model is updated
  3. The parameter table shows the new model's parameters
  4. The selectbox is a user convenience, not the source of truth
**Warning signs:** User confusion about which model is active
**Optional fix:** Add `key='model_selectbox'` and update via bridge

### Pitfall 2: Widget State Set After Widget Renders
**What goes wrong:** StreamlitAPIException raised
**Why it happens:** Streamlit's execution model processes script top-to-bottom; widgets "claim" their keys when rendered
**How to avoid:** State modifications happen in previous script run (tool execution), not current render
**Warning signs:** Exception message mentions "cannot be set after the widget is instantiated"
**Current protection:** Tools run in chat handler BEFORE st.rerun() triggers fresh render

### Pitfall 3: Stale Parameter Values After Model Change
**What goes wrong:** New model shows parameter values from previous model
**Why it happens:** Session state keys persist; new model has same-named parameters
**How to avoid:** Always call clear_parameter_widgets() before setting new model
**Warning signs:** Parameter values don't match model defaults
**Current protection:** set_model() tool calls bridge.clear_parameter_widgets()

### Pitfall 4: Atomic Updates Not Actually Atomic
**What goes wrong:** User briefly sees partial updates
**Why it happens:** Concern that multiple state updates render intermediate states
**Reality:** Streamlit renders ONLY after script completes, so batch updates appear atomic
**How to avoid:** Set all state in one pass before st.rerun()
**Current protection:** set_multiple_parameters() sets all values then calls needs_rerun once

### Pitfall 5: AI Chat Column vs Sidebar Rerun Check
**What goes wrong:** needs_rerun flag not checked in render_ai_chat_column()
**Why it happens:** Two different chat rendering functions exist
**Analysis:**
  - render_ai_chat_sidebar() checks needs_rerun (line 309)
  - render_ai_chat_column() just calls st.rerun() after every message (line 425)
**Current status:** Column version always reruns, so no issue
**Potential issue:** Sidebar version might not rerun if needs_rerun check fails

## Code Examples

Verified patterns from the existing codebase:

### Set-Model Tool Implementation (Already Complete)
```python
# Source: mcp_server.py lines 185-212
def set_model(model_name: str) -> str:
    if not _check_tools_enabled():
        return 'AI tools are disabled...'

    try:
        from sans_webapp.services.mcp_state_bridge import get_state_bridge

        fitter = get_fitter()
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
```

### Set-Parameter Tool Implementation (Already Complete)
```python
# Source: mcp_server.py lines 215-268
def set_parameter(
    name: str,
    value: float | None = None,
    min_bound: float | None = None,
    max_bound: float | None = None,
    vary: bool | None = None,
) -> str:
    # ... validation ...

    # Update fitter state
    if value is not None:
        param.value = value
    # ... bounds and vary ...

    # Update UI widgets via bridge
    bridge = get_state_bridge()
    bridge.set_parameter_widget(name, value=value, min_val=min_bound, max_val=max_bound, vary=vary)
    bridge.set_needs_rerun(True)

    return f"Parameter '{name}' updated: {', '.join(changes)}"
```

### Rerun Check in Sidebar (Already Complete)
```python
# Source: components/sidebar.py lines 308-312
# Check if UI refresh is needed (tools modified state)
if st.session_state.get('needs_rerun', False):
    st.session_state.needs_rerun = False

st.rerun()
```

### Bridge Parameter Widget Setter (Already Complete)
```python
# Source: mcp_state_bridge.py lines 208-228
def set_parameter_widget(
    self,
    param_name: str,
    value: float | None = None,
    min_val: float | None = None,
    max_val: float | None = None,
    vary: bool | None = None,
) -> None:
    """Set individual parameter widget state. Only sets provided values."""
    if value is not None:
        st.session_state[f'value_{param_name}'] = clamp_for_display(value)
    if min_val is not None:
        st.session_state[f'min_{param_name}'] = clamp_for_display(min_val)
    if max_val is not None:
        st.session_state[f'max_{param_name}'] = clamp_for_display(max_val)
    if vary is not None:
        st.session_state[f'vary_{param_name}'] = vary
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_state_accessor` pattern | SessionStateBridge | Phase 1 | Centralized state management |
| Direct st.session_state in tools | Bridge methods | Phase 1 | Typed, testable, consistent |
| Manual widget key management | Bridge abstracts keys | Phase 1 | Single source of truth |

**Already implemented in Phase 1:**
- All setter methods exist in SessionStateBridge
- All tools use bridge methods
- needs_rerun flag is set by all state-modifying tools
- Rerun check exists in sidebar chat handler

## Open Questions

Things that require verification during implementation:

1. **Model Selector Visual Update**
   - What we know: Selectbox has no key, so won't update visually
   - What's unclear: Is this acceptable UX or should we add key binding?
   - Recommendation: Document current behavior; optionally add key in Phase 2 if user confusion is observed

2. **render_ai_chat_column() Rerun Behavior**
   - What we know: It always calls st.rerun() after every message
   - What's unclear: Does this mean needs_rerun is redundant in column mode?
   - Recommendation: Verify both code paths trigger proper refresh

3. **Test Coverage for Sync Flow**
   - What we know: 114 tests pass, but unclear if sync flow is tested end-to-end
   - What's unclear: Are there integration tests for tool -> UI sync?
   - Recommendation: Add specific tests for each SYNC requirement

## Verification Requirements

### SYNC-01 Verification: set-model Tool
Test: When Claude calls `set-model "cylinder"`:
- [ ] Model selector shows... (optional - may not update due to no key)
- [ ] `st.session_state.current_model` == "cylinder"
- [ ] `st.session_state.model_selected` == True
- [ ] Old parameter widgets cleared
- [ ] New model's parameters appear in parameter table
- [ ] Fitter.model.name == "cylinder"

### SYNC-02 Verification: set-parameter Tool
Test: When Claude calls `set-parameter radius value=50`:
- [ ] `st.session_state['value_radius']` == 50 (clamped)
- [ ] Parameter table shows value 50 in the radius row
- [ ] Fitter.params['radius'].value == 50

### SYNC-03 Verification: set-multiple-parameters Tool
Test: When Claude calls `set-multiple-parameters {"radius": {"value": 50}, "scale": {"value": 1.0, "vary": true}}`:
- [ ] Both parameters update atomically (no partial visible state)
- [ ] `st.session_state['value_radius']` == 50
- [ ] `st.session_state['value_scale']` == 1.0
- [ ] `st.session_state['vary_scale']` == True
- [ ] Both values visible in parameter table after single rerun

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `mcp_state_bridge.py`, `mcp_server.py`, `parameters.py`, `sidebar.py`, `ai_chat.py`
- Phase 1 Research and Summary documents
- [Streamlit Session State Docs](https://docs.streamlit.io/develop/concepts/architecture/session-state) - Widget key patterns, execution model
- [Streamlit Widget State Updates](https://docs.streamlit.io/knowledge-base/using-streamlit/widget-updating-session-state) - Proper update patterns

### Secondary (MEDIUM confidence)
- [Streamlit 2026 Release Notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) - Latest behavior updates
- [Streamlit st.rerun() Docs](https://docs.streamlit.io/develop/api-reference/execution-flow/st.rerun) - Rerun API and behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing libraries in codebase
- Architecture: HIGH - Phase 1 implemented core patterns, Phase 2 verifies them
- Pitfalls: HIGH - Verified against codebase and official Streamlit documentation

**Research date:** 2026-02-05
**Valid until:** 30 days (stable implementation, verification focus)

---

## Implementation Guidance

Based on research, Phase 2 should focus on:

### Verification First
Most of the sync infrastructure is complete from Phase 1. The primary work is:
1. Writing integration tests for each SYNC requirement
2. Manual testing of the tool -> UI sync flow
3. Fixing any gaps discovered during verification

### Potential Code Changes

1. **Optional: Model Selector Key Binding**
   If verification shows user confusion, add key to model selectbox:
   ```python
   # sidebar.py - optional enhancement
   selected_model = st.selectbox(
       MODEL_SELECT_LABEL,
       options=all_models,
       index=...,
       key='model_selectbox',  # Add key binding
   )
   ```
   And add bridge method to update it (if needed).

2. **Test File: test_sync_flow.py**
   Create integration tests that verify end-to-end sync:
   - Mock tool execution
   - Verify session_state changes
   - Verify widget values after simulated rerun

### Success Criteria Mapping

| Requirement | Implementation Status | Verification Needed |
|-------------|----------------------|---------------------|
| SYNC-01 | Complete in mcp_server.py | Test model change flow |
| SYNC-02 | Complete in mcp_server.py | Test parameter update flow |
| SYNC-03 | Complete in mcp_server.py | Test batch update atomicity |
