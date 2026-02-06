# Phase 1: Infrastructure - Research

**Researched:** 2026-02-05
**Domain:** Streamlit session state management for MCP tool integration
**Confidence:** HIGH

## Summary

Phase 1 establishes the infrastructure for MCP tools to safely modify Streamlit session state and trigger UI refresh. The research analyzed the existing codebase architecture and Streamlit's session state patterns to identify the optimal approach.

The codebase already has a solid foundation:
- `SessionStateBridge` exists with getter methods and basic setters
- A `needs_rerun` flag pattern is partially implemented
- MCP tools are structured with clear read-only vs. state-modifying separation
- Widget keys follow a consistent naming convention (`value_`, `min_`, `max_`, `vary_`)

The gap is that state-modifying MCP tools currently access `st.session_state` directly via a passed accessor object, bypassing the bridge pattern. The bridge needs extension with parameter widget setters, and tools need refactoring to use these bridge methods.

**Primary recommendation:** Extend `SessionStateBridge` with typed setter methods for parameter widgets, then refactor all state-modifying tools to use bridge methods exclusively.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Streamlit | 1.40+ | Web app framework | Already in use, provides session_state API |
| FastMCP | 2.3+ | MCP server implementation | Already in use for tool definitions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing | stdlib | Type hints | All bridge method signatures |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Bridge pattern | Direct state access | Bridge centralizes all state mutations, making debugging easier |
| Singleton bridge | Instance per request | Singleton is simpler for single-user desktop app |

## Architecture Patterns

### Current Project Structure (Relevant Files)
```
src/sans_webapp/
├── services/
│   ├── mcp_state_bridge.py    # SessionStateBridge class (extend here)
│   ├── claude_mcp_client.py   # Tool execution routing
│   └── ai_chat.py             # Chat handling, rerun logic
├── mcp_server.py              # MCP tool implementations (refactor here)
├── components/
│   └── parameters.py          # Widget rendering (reference for keys)
└── app.py                     # Main app orchestration
```

### Pattern 1: Bridge-Mediated State Access
**What:** All MCP tool state modifications go through SessionStateBridge methods
**When to use:** Any time a tool needs to modify session state
**Example:**
```python
# Source: Existing pattern in mcp_state_bridge.py
from sans_webapp.services.mcp_state_bridge import get_state_bridge

def set_parameter(name: str, value: float | None = None, ...):
    bridge = get_state_bridge()

    # Use bridge methods instead of direct state access
    if value is not None:
        bridge.set_parameter_value(name, value)

    bridge.set_needs_rerun(True)
    return f"Parameter '{name}' updated"
```

### Pattern 2: Widget Key Naming Convention
**What:** Consistent key naming for parameter widgets enables programmatic updates
**When to use:** Any time a parameter widget state needs to be set or cleared
**Example:**
```python
# Source: Derived from components/parameters.py lines 171-174
# Widget keys follow this pattern:
value_key = f'value_{param_name}'   # e.g., 'value_radius'
min_key = f'min_{param_name}'       # e.g., 'min_radius'
max_key = f'max_{param_name}'       # e.g., 'max_radius'
vary_key = f'vary_{param_name}'     # e.g., 'vary_radius'
```

### Pattern 3: Rerun Flag Pattern
**What:** Set a flag in session state, check it after tool execution, then rerun
**When to use:** After any state-modifying tool completes
**Example:**
```python
# Source: Existing pattern in mcp_state_bridge.py and sidebar.py
# In tool:
bridge.set_needs_rerun(True)

# In UI after chat response (sidebar.py ~line 303):
if st.session_state.get('needs_rerun', False):
    st.session_state.needs_rerun = False
    st.rerun()
```

### Anti-Patterns to Avoid
- **Direct st.session_state access in tools:** Bypasses the bridge, loses type safety and centralized control
- **Setting widget state after widget renders:** Streamlit raises StreamlitAPIException if you set a widget key after its widget has rendered in the current script run
- **Missing needs_rerun flag:** UI won't update after tool executes, causing confusion

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| State access in tools | Direct `_state_accessor.key = value` | `SessionStateBridge.set_*()` methods | Centralized, typed, testable |
| Widget key generation | Inline `f'value_{name}'` everywhere | Bridge constants or methods | Single source of truth |
| Rerun coordination | Manual `st.rerun()` calls in tools | `needs_rerun` flag pattern | Tools don't know when UI is ready |

**Key insight:** The bridge pattern already exists and works for read operations. Extending it for write operations maintains consistency and avoids scattered state mutations.

## Common Pitfalls

### Pitfall 1: Setting Widget State After Rendering
**What goes wrong:** Streamlit raises `StreamlitAPIException` if you set a session_state key for a widget that has already rendered in the current script run
**Why it happens:** Streamlit's execution model processes the script top-to-bottom; widgets "claim" their keys when rendered
**How to avoid:** Set state BEFORE the widget renders (at script start or in a callback/previous run), never after
**Warning signs:** "StreamlitAPIException: st.session_state.value_radius cannot be set after the widget is instantiated"

### Pitfall 2: Forgetting to Clear Old Widget State on Model Change
**What goes wrong:** After changing models, old parameter widgets retain their values, causing mismatches
**Why it happens:** Different models have different parameters; session_state keys persist across reruns
**How to avoid:** Always call `clear_parameter_widgets()` before setting a new model
**Warning signs:** Parameter values from previous model appear in new model's parameters

### Pitfall 3: Rerun Called Inside Tool Execution
**What goes wrong:** Tool doesn't complete, state is inconsistent
**Why it happens:** `st.rerun()` halts script execution immediately
**How to avoid:** Tools set the `needs_rerun` flag; UI code checks it AFTER tool returns
**Warning signs:** Tool appears to hang or return incomplete results

### Pitfall 4: Widget Key Conflicts
**What goes wrong:** Multiple widgets share the same key, causing "DuplicateWidgetID" error
**Why it happens:** Dynamic widget creation without unique key management
**How to avoid:** Use consistent `{type}_{param_name}` pattern, clear on model change
**Warning signs:** DuplicateWidgetID exception at runtime

## Code Examples

Verified patterns from the existing codebase:

### Existing Parameter Widget Key Pattern
```python
# Source: components/parameters.py lines 171-184
for param_name, param_info in params.items():
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
    # ... similar for min, max
```

### Existing Bridge Rerun Methods
```python
# Source: mcp_state_bridge.py lines 88-98
def set_needs_rerun(self, value: bool = True) -> None:
    """Set the needs_rerun flag."""
    st.session_state.needs_rerun = value

def get_needs_rerun(self) -> bool:
    """Get the needs_rerun flag."""
    return st.session_state.get('needs_rerun', False)

def clear_needs_rerun(self) -> None:
    """Clear the needs_rerun flag."""
    st.session_state.needs_rerun = False
```

### Existing Clear Parameter Widgets
```python
# Source: mcp_state_bridge.py lines 178-189
def clear_parameter_widgets(self) -> None:
    """Clear all parameter widget state (for model changes)."""
    keys_to_remove = [
        k
        for k in st.session_state.keys()
        if k.startswith('value_')
        or k.startswith('min_')
        or k.startswith('max_')
        or k.startswith('vary_')
    ]
    for key in keys_to_remove:
        del st.session_state[key]
```

### Current Tool Pattern (To Be Refactored)
```python
# Source: mcp_server.py lines 259-262 - Current direct access pattern
if _state_accessor is not None:
    _state_accessor.needs_rerun = True

# Target pattern after refactoring:
bridge = get_state_bridge()
bridge.set_needs_rerun(True)
```

### Required New Bridge Methods (To Be Implemented)
```python
# Pattern for new methods to add to SessionStateBridge
def set_parameter_value(self, param_name: str, value: float) -> None:
    """Set parameter value widget state."""
    key = f'value_{param_name}'
    st.session_state[key] = clamp_for_display(value)

def set_parameter_bounds(self, param_name: str, min_val: float, max_val: float) -> None:
    """Set parameter bounds widget state."""
    st.session_state[f'min_{param_name}'] = clamp_for_display(min_val)
    st.session_state[f'max_{param_name}'] = clamp_for_display(max_val)

def set_parameter_vary(self, param_name: str, vary: bool) -> None:
    """Set parameter vary checkbox state."""
    st.session_state[f'vary_{param_name}'] = vary

def set_parameter_widget(
    self,
    param_name: str,
    value: float | None = None,
    min_val: float | None = None,
    max_val: float | None = None,
    vary: bool | None = None
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
| `st.experimental_rerun()` | `st.rerun()` | Streamlit 1.27 | API renamed, same behavior |
| Per-widget state variables | Unified session_state | Streamlit 1.10+ | Simpler state management |
| Direct state accessor | Bridge pattern | This project | Centralized, typed state access |

**Deprecated/outdated:**
- `st.experimental_rerun()`: Use `st.rerun()` instead (already done in codebase)
- `_state_accessor` pattern: Should migrate to bridge pattern (this phase's work)

## Open Questions

Things that couldn't be fully resolved:

1. **Polydispersity widget state keys**
   - What we know: PD widgets use `pd_width_`, `pd_n_`, `pd_type_`, `pd_vary_` prefixes
   - What's unclear: Should bridge have separate PD methods or unified parameter methods?
   - Recommendation: Start with basic parameter methods (value/min/max/vary); PD methods can be added in Phase 3 when implementing SYNC-05

2. **Atomic multi-parameter updates**
   - What we know: `set-multiple-parameters` tool updates multiple params
   - What's unclear: Does Streamlit handle batch updates atomically, or do intermediate states render?
   - Recommendation: Set all state changes in a single pass before rerun; Streamlit only renders after script completes, so this should be atomic from user's perspective

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `mcp_state_bridge.py`, `mcp_server.py`, `parameters.py`, `sidebar.py`
- [Streamlit Session State Docs](https://docs.streamlit.io/develop/concepts/architecture/session-state) - Widget key patterns, execution model
- [Streamlit st.rerun() Docs](https://docs.streamlit.io/develop/api-reference/execution-flow/st.rerun) - Rerun API and behavior

### Secondary (MEDIUM confidence)
- [Streamlit 2026 Release Notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) - Latest widget behavior updates
- [Streamlit Widget State Synchronization](https://docs.streamlit.io/knowledge-base/using-streamlit/widget-updating-session-state) - Specific patterns for widget updates

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing libraries in codebase
- Architecture: HIGH - Extending existing patterns already in use
- Pitfalls: HIGH - Verified against official Streamlit documentation

**Research date:** 2026-02-05
**Valid until:** 60 days (stable Streamlit patterns, internal refactoring)

---

## Implementation Checklist

Based on research, here are the specific tasks for Phase 1:

### INFRA-01: Extend SessionStateBridge
- [ ] Add `set_parameter_value(param_name, value)` method
- [ ] Add `set_parameter_bounds(param_name, min_val, max_val)` method
- [ ] Add `set_parameter_vary(param_name, vary)` method
- [ ] Add `set_parameter_widget(param_name, value?, min?, max?, vary?)` convenience method
- [ ] Ensure `clear_parameter_widgets()` is complete (already exists)

### INFRA-02: Refactor Tools to Use Bridge
- [ ] Remove `set_state_accessor()` pattern from `mcp_server.py`
- [ ] Import `get_state_bridge()` in `mcp_server.py`
- [ ] Refactor `set_model()` to use bridge methods
- [ ] Refactor `set_parameter()` to use bridge methods
- [ ] Refactor `set_multiple_parameters()` to use bridge methods
- [ ] Refactor other state-modifying tools (run_fit, enable_polydispersity, structure factor)

### INFRA-03: Automatic UI Rerun
- [ ] Verify `needs_rerun` flag is set by all state-modifying tools via bridge
- [ ] Verify UI checks `needs_rerun` after chat response (already done in sidebar.py)
- [ ] Verify `st.rerun()` is called when flag is true (already done in sidebar.py)
