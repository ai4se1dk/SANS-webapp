# Coding Conventions

**Analysis Date:** 2026-02-05

## Naming Patterns

**Files:**
- Lowercase with underscores: `ai_chat.py`, `session_state.py`, `sans_types.py`
- Component files use descriptive names in `components/`: `sidebar.py`, `parameters.py`, `data_preview.py`, `fit_results.py`
- Service modules live in `services/`: `ai_chat.py`, `claude_mcp_client.py`, `session_state.py`, `mcp_state_bridge.py`
- TypedDict type definitions grouped in `sans_types.py`
- UI constants centralized in `ui_constants.py`
- Private/helper functions prefixed with underscore: `_get_example_data_path()`, `_build_context()`, `_ensure_mcp_initialized()`

**Functions:**
- Snake_case: `init_session_state()`, `render_data_upload_sidebar()`, `suggest_models_ai()`
- Boolean check functions prefixed with `is_` or `get_`: `is_data_loaded()`, `is_model_selected()`, `get_fitter()`
- Render functions prefixed with `render_`: `render_parameter_configuration()`, `render_ai_chat_column()`, `render_fit_results()`
- Apply/update functions prefixed with `apply_`: `apply_param_updates()`, `apply_pd_updates()`, `apply_fit_results_to_params()`
- Build/create functions prefixed with `build_`: `build_param_updates_from_params()`, `_build_context()`
- Private function prefix `_`: `_send_chat_message_openai()`, `_send_chat_message_claude()`, `_ensure_mcp_initialized()`

**Variables:**
- Snake_case: `param_updates`, `fit_result`, `mock_session_state`, `context_parts`
- Session state keys use snake_case with prefixes for grouping: `value_radius`, `min_radius`, `max_radius`, `vary_radius`
- Prefixes for parameter UI state: `value_`, `min_`, `max_`, `vary_`, `pd_width_`, `pd_n_`, `pd_type_`, `pd_vary_`
- Boolean flags: `expand_fitting`, `data_loaded`, `model_selected`, `fit_completed`, `ai_tools_enabled`, `needs_rerun`

**Types (TypedDict and Classes):**
- PascalCase: `ParamInfo`, `MCPToolResult`, `ChatMessage`, `FitResult`, `ParamUpdate`, `PDUpdate`, `FitParamInfo`
- TypedDict suffixes: `Info` for data structures, `Result` for operation results, `Update` for state changes
- Mock classes for testing: `MockSessionState`, `MockFitter`

## Code Style

**Formatting:**
- Ruff is the formatter and linter
- Line length: 100 characters (configured in `pyproject.toml`)
- Python target version: 3.9+

**Linting:**
- Ruff check config in `pyproject.toml`:
  - E: pycodestyle errors
  - W: pycodestyle warnings
  - F: pyflakes
  - I: isort (import sorting)
  - B: flake8-bugbear
  - C4: flake8-comprehensions
  - UP: pyupgrade
  - Q: flake8-quotes
- Ignored rules:
  - E501: line too long (handled by formatter)
  - B008: function calls in argument defaults
  - W191: tabs in indentation
  - Q001: single quotes for multiline (conflicts with formatter)
- Per-file ignores:
  - `__init__.py`: F401 (unused imports allowed for re-exports)
  - `tests/*`: F401, F811 (unused imports and function redefinitions allowed)

**Quotes:**
- Single quotes for strings: `'data'`, `'parameter'`
- Multiline strings use single quotes (configured in ruff.format)

## Import Organization

**Order:**
1. Standard library imports: `typing`, `os`, `tempfile`, `pathlib`
2. Third-party imports: `numpy`, `streamlit`, `pytest`, `sans_fitter`
3. Local application imports: `from sans_webapp.components import ...`, `from sans_webapp.services import ...`

**Examples:**
```python
from typing import Optional, cast

import numpy as np
import streamlit as st
from sans_fitter import SANSFitter

from sans_webapp.sans_types import FitResult, ParamInfo
from sans_webapp.services.ai_chat import suggest_models_ai
from sans_webapp.ui_constants import APP_TITLE
```

**Path Aliases:**
- No import aliases configured; use full module paths
- Re-export pattern for backwards compatibility: `from sans_fitter import get_all_models  # noqa: F401 - re-exported`

## Error Handling

**Patterns:**
- Broad exception catching with context-aware messages:
  ```python
  try:
      result = fitter.fit(engine=engine, method=method)
      st.session_state.fit_completed = True
  except Exception as e:
      st.sidebar.error(f'Fitting error: {str(e)}')
  ```
- Defensive logging for non-critical failures:
  ```python
  try:
      client = get_claude_client(api_key)
  except Exception as e:  # pragma: no cover - defensive logging
      print(f"Warning: failed to initialize MCP/AI client: {e}")
  ```
- Session state for error storage (UI-friendly):
  ```python
  except Exception as e:
      st.session_state.ai_client_error = str(e)
  ```
- Return fallback values instead of raising:
  ```python
  except Exception as e:
      print(f'AI suggestion error: {e}')
      return ['sphere', 'cylinder', 'ellipsoid']  # Sensible default
  ```
- Pass exceptions down to caller when appropriate:
  ```python
  except ValueError:
      if api_key:
          reset_client()
          client = get_claude_client(api_key)
      else:
          return "Error: Anthropic API key not configured."
  ```

## Logging

**Framework:** `print()` for non-Streamlit contexts

**Patterns:**
- Print warnings during initialization: `print(f"Warning: failed to initialize MCP/AI client: {e}")`
- Store errors in session state for UI display: `st.session_state.ai_client_error = str(e)`
- Use Streamlit UI for user-facing messages:
  - `st.error()` for errors
  - `st.warning()` for warnings
  - `st.success()` for success messages
  - `st.info()` for informational messages

## Comments

**When to Comment:**
- Module-level docstrings required (shown in all files)
- Function docstrings for public API functions with parameters and return types
- Inline comments for non-obvious logic
- Pragmatic comments prefixed with markers:
  - `# pragma: no cover` for defensive code that's hard to test
  - `# noqa: F401` for re-exported imports allowed in `__init__.py`
  - `# noqa: F811` for allowed function redefinitions in tests

**JSDoc/TSDoc:**
Python uses standard docstring format with sections:
```python
def send_chat_message(user_message: str, api_key: Optional[str], fitter: SANSFitter) -> str:
    """
    Send a chat message and return an AI response.

    Args:
        user_message: The user's prompt
        api_key: Anthropic API key
        fitter: The SANSFitter instance with current context

    Returns:
        The AI response text
    """
```

## Function Design

**Size:** Functions typically range from 5-50 lines

**Parameters:**
- Use type hints always: `def init_session_state() -> None:`
- Named parameters for clarity: `st.selectbox(FIT_ENGINE_LABEL, FIT_ENGINE_OPTIONS, help=FIT_ENGINE_HELP, key='fit_engine')`
- Optional parameters use `Optional[Type]` or `Type | None` (Python 3.10+)
- Avoid function calls in argument defaults (B008 rule is on ignore list but generally avoided)

**Return Values:**
- Use None for side-effect functions: `def init_session_state() -> None:`
- Use TypedDict for complex returns: `-> dict[str, ParamUpdate]`
- Return tuples for multiple values: `-> tuple[str, list[str], bool]`
- Return sensible defaults instead of raising in service functions

## Module Design

**Exports:**
- No barrel exports used; files imported directly
- Re-export for backwards compatibility explicitly marked: `# noqa: F401 - re-exported for backwards compatibility`
- Functions organized by responsibility within modules

**Barrel Files:**
- `__init__.py` in packages is minimal (only re-exports)
- Each module imports from its actual implementation file

**Organization Pattern:**
- Utility/analysis functions: `sans_analysis_utils.py`
- Service layer: `services/` (ai_chat, claude_mcp_client, session_state, mcp_state_bridge)
- UI components: `components/` (sidebar, parameters, data_preview, fit_results)
- Type definitions: `sans_types.py`
- UI strings: `ui_constants.py`
- Main app logic: `app.py`

## Streamlit-Specific Conventions

**Session State:**
- Initialize defaults in `init_session_state()`: all session keys have explicit initialization
- Use session state getters for reading: `st.session_state.get(key, default)`
- Use `in` operator to check existence: `if 'ai_tools_enabled' in st.session_state`
- Store Streamlit keys as strings: `key='fit_engine'`

**UI Constants:**
- All UI strings stored in `ui_constants.py`
- Pattern: UPPERCASE_WITH_UNDERSCORES for constant names
- Constants imported directly from ui_constants module

---

*Convention analysis: 2026-02-05*
