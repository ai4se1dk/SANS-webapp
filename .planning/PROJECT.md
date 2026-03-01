# SANS-webapp MCP Integration

## What This Is

A Streamlit-based web application for Small-Angle Neutron Scattering (SANS) data analysis with an integrated AI assistant (Claude) that can directly manipulate the fitting workflow through MCP tools. The AI can load models, adjust parameters, run fits, and interpret results - providing an intelligent copilot for scientific data analysis.

## Core Value

**AI-driven state changes must be immediately visible in the UI.** When Claude uses a tool to modify model parameters or run a fit, the user sees the changes reflected in real-time. This bidirectional sync is what makes the AI assistant feel like a true collaborator rather than a disconnected chat interface.

## Requirements

### Validated

- ✓ Data upload and preview (CSV/DAT files with Q, I, dI columns) — existing
- ✓ Manual model selection from sasmodels library — existing
- ✓ AI-suggested model selection via Claude — existing
- ✓ Parameter configuration with value/min/max/vary controls — existing
- ✓ Polydispersity configuration for size parameters — existing
- ✓ Curve fitting with bumps/lmfit engines — existing
- ✓ Fit results display with chi-squared and parameter uncertainties — existing
- ✓ AI chat interface with conversation history — existing
- ✓ MCP tool definitions for all major operations — existing
- ✓ Read-only MCP tools work correctly (list-models, get-state, get-results) — existing

### Active

- [ ] **SYNC-01**: `set-model` tool updates UI immediately (model name, parameter table)
- [ ] **SYNC-02**: `set-parameter` tool updates UI widgets (value/min/max/vary inputs)
- [ ] **SYNC-03**: `set-multiple-parameters` tool updates all affected UI widgets
- [ ] **SYNC-04**: `run-fit` tool triggers fit result display and plot update
- [ ] **SYNC-05**: `enable-polydispersity` tool updates PD configuration UI
- [ ] **SYNC-06**: Structure factor tools update model configuration UI
- [ ] **SYNC-07**: All state-modifying tools trigger automatic UI refresh

### Out of Scope

- User authentication/RBAC — not needed for single-user desktop use
- Persistent storage of fit results — session-only scope for this milestone
- Background/async fitting — fitting is fast enough for interactive use
- Multi-model comparison in single session — manual workflow is sufficient

## Context

**Current State:**
The MCP integration is partially working. Claude can successfully invoke tools, and the tools execute correctly on the SANSFitter backend. However, there's a state synchronization gap:

1. **UI widgets bind to session state keys** (e.g., `value_radius`, `min_radius`, `vary_radius`)
2. **MCP tools modify fitter state directly** (e.g., `fitter.params['radius'].value = 50`)
3. **Widget initialization only happens if keys don't exist** — stale values persist

The `SessionStateBridge` class exists but is underutilized. It has a `clear_parameter_widgets()` method that's not called by MCP tools, and lacks methods to *set* parameter widget state.

**Error Pattern:**
User asks Claude to "set the sphere radius to 50 angstroms". Claude calls `set-parameter(name='radius', value=50)`. The fitter's internal state updates, but the UI still shows the old value. Claude may then call `get-current-state()` and see the correct value, but the user sees a discrepancy.

**Files Involved:**
- `src/sans_webapp/mcp_server.py` — tool implementations
- `src/sans_webapp/services/mcp_state_bridge.py` — state sync utilities (needs extension)
- `src/sans_webapp/components/parameters.py` — UI widget rendering
- `src/sans_webapp/components/sidebar.py` — chat handling and rerun logic

## Constraints

- **Tech stack**: Streamlit session state is the persistence layer; no external database
- **Compatibility**: Must not break existing manual workflows (button-driven parameter updates)
- **Performance**: State sync should not add noticeable latency to tool execution

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Auto-refresh UI after tool execution | User wants immediate feedback; "needs_rerun" flag already exists | — Pending |
| Extend SessionStateBridge for parameter sync | Centralized approach vs. inline code in each tool | — Pending |
| All state-modifying tools require sync | Consistent behavior; user chose "all tools" scope | — Pending |

---
*Last updated: 2026-02-05 after initialization*
