# 03-02 Summary: run-fit Param Sync (SYNC-04) & Structure Factor Widget Clearing (SYNC-06)

**Status:** COMPLETE
**Date:** 2026-02-06

## What Was Done

### Task 1: Refactored run_fit to sync fitted parameter values (SYNC-04)

In `run_fit()` in [mcp_server.py](src/sans_webapp/mcp_server.py), after `set_fit_completed` and `set_fit_result`, added a loop that:

- Iterates `fitter.params` and for each **varied** parameter calls `bridge.set_parameter_value(name, fitted_value)` so UI widgets immediately show fitted values.
- If a varied parameter ends with `_pd` (polydispersity width), also calls `bridge.set_pd_widget(base_param, pd_width=fitted_value)` to sync the PD widget.
- `bridge.set_needs_rerun(True)` is called **after** all syncs to trigger a single UI refresh.

### Task 2: Refactored structure factor tools (SYNC-06)

Both `set_structure_factor()` and `remove_structure_factor()` now call `bridge.clear_parameter_widgets()` **before** modifying the structure factor on the fitter. This ensures the UI reinitializes widgets from scratch on rerun, picking up added/removed SF parameters.

### Task 3: Tests and linting

- **129 tests passed**, 3 skipped, 0 failures
- **ruff check**: All checks passed

## Success Criteria

- [x] `run_fit` contains loop syncing varied parameters via `bridge.set_parameter_value()`
- [x] `run_fit` syncs PD parameters (ending with `_pd`) via `bridge.set_pd_widget()`
- [x] `set_structure_factor` calls `bridge.clear_parameter_widgets()` before `fitter.set_structure_factor()`
- [x] `remove_structure_factor` calls `bridge.clear_parameter_widgets()` before `fitter.remove_structure_factor()`
- [x] All tests pass (129)
- [x] Ruff linting passes

## Files Modified

| File | Change |
|------|--------|
| `src/sans_webapp/mcp_server.py` | `run_fit`: added fitted parameter → widget sync loop; `set_structure_factor` & `remove_structure_factor`: added `clear_parameter_widgets()` before SF mutation |
