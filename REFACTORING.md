# Refactoring Recommendations for app.py

Based on analysis of `src/app.py` (~1040 lines), here are the key refactoring recommendations for size and clarity.

## 1. Extract UI Constants to a Separate Module

Lines 214-355 contain ~140 lines of string constants. Move these to a dedicated file like `ui_constants.py` or `strings.py`. This would:

- Reduce `app.py` by ~140 lines
- Make localization easier
- Keep the main logic cleaner

## 2. Split into Logical Modules

The file mixes several concerns. Consider creating:

| New Module | Functions to Extract |
|-----------|---------------------|
| `sidebar.py` | `render_data_upload_sidebar()`, `render_model_selection_sidebar()`, `render_ai_chat_sidebar()` |
| `parameters.py` | `render_parameter_table()`, `apply_pending_preset()`, `apply_fit_results_to_params()`, `apply_param_updates()`, `build_param_updates_from_params()` |
| `ai_chat.py` | `send_chat_message()`, `suggest_models_ai()`, chat context building logic |
| `fit_results.py` | Fit results display logic (~lines 878-1010) |

## 3. Extract the Long `main()` Function

The `main()` function (lines 767-1037) is ~270 lines. Break it into:

- `render_data_preview()` - data visualization section
- `render_parameter_configuration()` - parameter form and presets
- `render_fit_controls()` - fitting engine selection
- `render_fit_results()` - results display, slider, export

## 4. Move TypedDicts to a `types.py` Module

The `ParamInfo`, `FitParamInfo`, `FitResult`, and `ParamUpdate` classes (lines 30-53) belong in a shared types file.

## 5. Simplify Repetitive Code

The parameter table column headers (lines 146-150) could be a loop:

```python
for i, label in enumerate(PARAMETER_COLUMNS_LABELS):
    param_cols[i].markdown(label)
```

## 6. Remove Unused CSS/Functions

`inject_right_sidebar_css()` (lines 447-491) appears unused—the right sidebar CSS is never actually injected in `main()`.

## 7. Consolidate Session State Management

Session state operations are scattered throughout. Consider a dedicated `SessionState` class or module to centralize:

- Initialization logic
- Pending operations (`pending_preset`, `pending_update_from_fit`)
- Widget state keys (`value_`, `min_`, `max_`, `vary_`)

## Suggested Final Structure

```
src/
  app.py              # ~150 lines: main() orchestration only
  ui_constants.py     # All string constants
  types.py            # TypedDicts
  components/
    sidebar.py        # Sidebar rendering
    parameters.py     # Parameter table and updates  
    fit_results.py    # Fit results display
    data_preview.py   # Data visualization
  services/
    ai_chat.py        # AI chat logic
    session_state.py  # State management
```

## Expected Results

This refactoring would reduce `app.py` from **~1040 lines to ~150 lines** while improving:

- **Testability**: Smaller, focused modules are easier to unit test
- **Maintainability**: Changes to one feature don't risk breaking others
- **Readability**: Each file has a single, clear responsibility
- **Reusability**: Components can be reused in other apps if needed
