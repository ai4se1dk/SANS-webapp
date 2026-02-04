# Coding Conventions

**Analysis Date:** 2026-02-04

## Naming Patterns

**Files:**
- Snake case for all Python files: `sans_analysis_utils.py`, `openai_client.py`, `session_state.py`
- Component files in dedicated directories: `components/data_preview.py`, `components/parameters.py`
- Service files in `services/` directory: `services/ai_chat.py`, `services/session_state.py`
- Constants file: `ui_constants.py` (centralized for localization-friendly UI strings)
- Type definitions file: `sans_types.py` (all TypedDict definitions)

**Functions:**
- Snake case: `render_fitting_sidebar()`, `analyze_data_for_ai_suggestion()`, `clear_parameter_state()`
- Private helper functions prefixed with underscore: `_get_example_data_path()`
- Descriptive verb-prefixed names: `render_*`, `apply_*`, `build_*`, `send_*`, `get_*`, `is_*`, `suggest_*`
- Async-compatible naming: No async wrappers detected; synchronous throughout

**Variables:**
- Snake case: `q_data`, `i_data`, `api_key`, `param_updates`, `chat_api_key`
- Session state keys prefixed with underscore for clarity: `value_radius`, `min_radius`, `max_radius`, `vary_radius`
- Descriptive prefix patterns for session state: `'value_'`, `'min_'`, `'max_'`, `'vary_'`, `'pd_'` for polydispersity parameters
- Configuration variables in UPPERCASE: `MAX_FLOAT_DISPLAY`, `MIN_FLOAT_DISPLAY`, `APP_PAGE_TITLE`

**Types:**
- PascalCase for TypedDict classes: `ParamInfo`, `FitParamInfo`, `FitResult`, `ParamUpdate`, `PDUpdate`
- Type hints use modern Python 3.10+ syntax: `dict[str, ParamUpdate]`, `list[str]`, `str | None`
- Optional parameters use union syntax: `api_key: str | None` instead of `Optional[str]`

## Code Style

**Formatting:**
- Ruff used for both linting and formatting
- Line length: 100 characters (from `pyproject.toml` - `line-length = 100`)
- Quote style: Single quotes for strings (`inline-quotes = "single"`, `multiline-quotes = "single"`)
- Indentation: 4 spaces (implicit Python standard)

**Linting:**
- Ruff linter with comprehensive rule selection:
  - E, W: pycodestyle errors and warnings
  - F: pyflakes (undefined names, unused imports)
  - I: isort (import sorting)
  - B: flake8-bugbear (common bugs)
  - C4: flake8-comprehensions
  - UP: pyupgrade
  - Q: flake8-quotes
- Ignored rules: E501 (line too long - handled by formatter), B008 (function calls in defaults), W191 (tabs), Q001 (multiline string quotes)
- Per-file ignores:
  - `__init__.py`: F401 (unused imports allowed for re-exports)
  - `tests/*`: F401, F811 (unused imports and redefinitions allowed)

## Import Organization

**Order:**
1. Standard library imports: `import sys`, `from pathlib import Path`, `from typing import Optional`
2. Third-party imports: `import numpy as np`, `import streamlit as st`, `from sans_fitter import SANSFitter`
3. Local imports: `from sans_webapp.services.session_state import init_session_state`
4. Internal re-exports for backward compatibility with `# noqa: F401` comment

**Path Aliases:**
- No explicit aliases configured; uses standard relative imports
- Re-exports used strategically: `get_all_models` re-exported in `sans_analysis_utils.py` for backwards compatibility

**Examples from codebase:**
```python
# From src/sans_webapp/app.py (line 15-43)
from typing import cast

import streamlit as st
from sans_fitter import get_all_models  # noqa: F401 - re-exported for backwards compatibility

from sans_webapp.components.data_preview import render_data_preview
from sans_webapp.components.fit_results import render_fit_results
from sans_webapp.sans_analysis_utils import analyze_data_for_ai_suggestion  # noqa: F401 - re-exported
```

## Error Handling

**Patterns:**
- Try-except blocks with specific exception handling for expected failures
- Generic exception handling for user-facing operations (fitting):
  ```python
  # From src/sans_webapp/app.py (line 120-131)
  with st.spinner(f'Fitting with {engine}/{method}...'):
      try:
          any_vary = any(p['vary'] for p in fitter.params.values())
          if not any_vary:
              st.sidebar.warning(WARNING_NO_VARY)
          else:
              result = fitter.fit(engine=engine, method=method)
              st.session_state.fit_completed = True
      except Exception as e:
          st.sidebar.error(f'Fitting error: {str(e)}')
  ```
- Streamlit UI feedback for errors: `st.error()`, `st.warning()`, `st.sidebar.error()`
- Graceful fallbacks for optional operations:
  ```python
  # From src/sans_webapp/components/sidebar.py (line 62-81)
  def _get_example_data_path() -> Path | None:
      """Get the path to the example data file bundled with the package."""
      try:
          package_files = files('sans_webapp')
          example_path = package_files / 'data' / EXAMPLE_DATA_FILE
          if hasattr(example_path, 'is_file') and example_path.is_file():
              return Path(str(example_path))
      except (TypeError, FileNotFoundError):
          pass
      # Fallback: check current working directory
      cwd_path = Path.cwd() / EXAMPLE_DATA_FILE
      if cwd_path.exists():
          return cwd_path
  ```

## Logging

**Framework:** Print-based debugging in tests; Streamlit UI components for user feedback in app

**Patterns:**
- Test output uses `print()` for progress: `print('Testing get_all_models() from sans_fitter...')`
- User feedback uses Streamlit widgets:
  - `st.success()` for successful operations
  - `st.warning()` for warnings
  - `st.error()` for errors
  - `st.info()` for informational messages
  - `st.sidebar.*` variants for sidebar placement
- No centralized logging framework; relies on print() for debug output

## Comments

**When to Comment:**
- Module-level docstrings required for all files
- Function docstrings required (Google-style format with Args, Returns sections)
- Inline comments for complex logic or non-obvious decisions
- HTML/CSS/JavaScript embedded in Streamlit calls documented inline

**Examples:**
```python
# From src/sans_webapp/services/session_state.py (line 37-50)
def clamp_for_display(value: float) -> float:
    """
    Clamp a value to a range that Streamlit's number_input can handle.
    Converts inf/-inf to displayable bounds.

    Args:
        value: The value to clamp

    Returns:
        The clamped value
    """
```

**JSDoc/TSDoc:** Not applicable (Python project)

## Function Design

**Size:** No strict line limits enforced; functions range from 5 lines (trivial getters) to 100+ lines (complex UI rendering)

**Parameters:**
- Use keyword-only arguments with `*` separator for clarity:
  ```python
  # From src/sans_webapp/openai_client.py (line 9-15)
  def create_chat_completion(
      *,
      api_key: str,
      model: str,
      messages: Iterable[dict[str, str]],
      max_tokens: int,
  ) -> Any:
  ```
- Positional parameters for data: `q_data: np.ndarray`, `i_data: np.ndarray`
- Type hints mandatory on all parameters and return types

**Return Values:**
- Explicit return type annotations: `-> None`, `-> str`, `-> dict[str, ParamUpdate]`
- Optional returns use union syntax: `-> Path | None`
- Streamlit rendering functions return `None` (side effects only)

## Module Design

**Exports:**
- Use `__all__` list for public API definition:
  ```python
  # From src/sans_webapp/sans_analysis_utils.py (line 15-23)
  __all__ = [
      'get_all_models',
      'analyze_data_for_ai_suggestion',
      'suggest_models_simple',
      'plot_data_and_fit',
      'calculate_residuals',
      'plot_data_fit_and_residuals',
  ]
  ```
- Single responsibility per module: components, services, utilities are separated
- Business logic isolated from UI (e.g., `sans_analysis_utils.py` has no Streamlit dependency)

**Barrel Files:**
- Component barrel file at `components/__init__.py` re-exports all rendering functions:
  ```python
  # From src/sans_webapp/components/__init__.py
  from sans_webapp.components.data_preview import render_data_preview
  from sans_webapp.components.fit_results import render_fit_results
  # ... more imports
  __all__ = [
      'render_data_preview',
      'render_fit_results',
      # ... more exports
  ]
  ```
- Services have minimal re-exports; mostly direct imports

## TypedDict Usage

**Pattern:** TypedDict classes used extensively for type-safe dictionaries representing domain models:
```python
# From src/sans_webapp/sans_types.py
class ParamInfo(TypedDict):
    """Parameter information from the fitter."""
    value: float
    min: float
    max: float
    vary: bool
    description: str | None

class FitResult(TypedDict, total=False):
    """Fit result containing chi-squared and parameters."""
    chisq: float
    parameters: dict[str, FitParamInfo]
```
- `total=False` used for optional fields in fit results
- Type hints in function signatures use these TypedDicts: `def apply_param_updates(fitter: SANSFitter, param_updates: dict[str, ParamUpdate]) -> None`

---

*Convention analysis: 2026-02-04*
