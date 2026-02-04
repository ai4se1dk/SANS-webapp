# Codebase Structure

**Analysis Date:** 2026-02-04

## Directory Layout

```
C:\Users\piotr\projects\ai\SANS-webapp/
├── src/                                    # Main source code
│   ├── sans_webapp/                        # Main package
│   │   ├── __init__.py                     # Package init (re-exports for backwards compatibility)
│   │   ├── __main__.py                     # CLI entry point
│   │   ├── app.py                          # Main Streamlit application
│   │   ├── openai_client.py                # OpenAI API wrapper
│   │   ├── sans_types.py                   # TypedDict definitions
│   │   ├── sans_analysis_utils.py          # SANS analysis utilities (no UI dependencies)
│   │   ├── ui_constants.py                 # UI string constants and configuration
│   │   ├── components/                     # UI rendering components
│   │   │   ├── __init__.py
│   │   │   ├── data_preview.py             # Data visualization component
│   │   │   ├── fit_results.py              # Fit results display component
│   │   │   ├── parameters.py               # Parameter configuration component
│   │   │   └── sidebar.py                  # Sidebar components (data upload, model selection, AI chat)
│   │   ├── services/                       # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── ai_chat.py                  # AI chat and model suggestion logic
│   │   │   └── session_state.py            # Session state initialization and helpers
│   │   ├── data/                           # Data files
│   │   │   └── simulated_sans_data.csv     # Example SANS data file
│   │   └── sans_webapp.egg-info/           # Package metadata (generated)
│   └── demo_app.py                         # Demo application (separate from main)
├── tests/                                  # Test suite
│   ├── __init__.py
│   ├── test_app.py                         # Application tests
│   └── test_polydispersity.py              # Polydispersity feature tests
├── .planning/                              # Planning and analysis documents
│   └── codebase/                           # Codebase documentation (this location)
├── .github/                                # GitHub configuration
├── .vscode/                                # VS Code settings
├── pyproject.toml                          # Project configuration and dependencies
├── pixi.lock                               # Pixi lock file (environment snapshots)
├── Dockerfile                              # Container configuration
├── Procfile                                # Heroku deployment config
├── setup.sh                                # Setup script
├── README.md                               # Project documentation
├── PROJECT_STRUCTURE.md                    # Original structure documentation
├── AGENTS.md                               # AI agent instructions
├── MCP_SANS.md                             # MCP server documentation
└── QUICKSTART.md                           # Quick start guide

```

## Directory Purposes

**src/sans_webapp/:**
- Purpose: Main application package
- Contains: Entry points, UI rendering, business logic, utilities
- Key files: `app.py` (main orchestrator), `sans_types.py` (type contracts)

**src/sans_webapp/components/:**
- Purpose: Streamlit UI rendering functions
- Contains: Four component modules for different page sections
- Key files: `sidebar.py` (largest, ~340 lines), `parameters.py` (parameter UI management)
- Pattern: Functions named `render_*()` that take fitter/session state, return None (side effects via st.*)

**src/sans_webapp/services/:**
- Purpose: Business logic separate from UI framework
- Contains: State management and AI service integration
- Key files: `session_state.py` (initializes all session defaults), `ai_chat.py` (OpenAI integration)

**src/sans_webapp/data/:**
- Purpose: Package data resources (bundled with installation)
- Contains: Example SANS data file for demo purposes
- Referenced in: `sidebar.py` via importlib.resources

**tests/:**
- Purpose: Unit and integration tests
- Contains: Test files for app logic and features
- Pattern: pytest with markers (slow, integration, unit)
- Run: `pytest tests/ -v` or `pixi run test`

## Key File Locations

**Entry Points:**
- `src/sans_webapp/__main__.py`: CLI entry, delegates to Streamlit
- `src/sans_webapp/app.py`: Main Streamlit app, orchestrates all rendering

**Configuration:**
- `pyproject.toml`: Dependencies, build config, ruff/pytest configuration
- `src/sans_webapp/ui_constants.py`: All UI strings and constants
- `src/sans_webapp/sans_types.py`: Type definitions for data contracts

**Core Logic:**
- `src/sans_webapp/services/ai_chat.py`: OpenAI integration and model suggestions
- `src/sans_webapp/services/session_state.py`: Session state initialization
- `src/sans_webapp/sans_analysis_utils.py`: SANS data analysis (plotting, heuristics)

**UI Components:**
- `src/sans_webapp/components/sidebar.py`: Data upload, model selection, AI chat
- `src/sans_webapp/components/parameters.py`: Parameter configuration table/widgets
- `src/sans_webapp/components/data_preview.py`: Data visualization and statistics
- `src/sans_webapp/components/fit_results.py`: Fit results display

**External Integration:**
- `src/sans_webapp/openai_client.py`: OpenAI API wrapper (abstraction layer)

**Testing:**
- `tests/test_app.py`: Main application tests
- `tests/test_polydispersity.py`: Polydispersity feature tests

## Naming Conventions

**Files:**
- `*.py`: Standard Python modules
- Component modules: `{feature_area}.py` (e.g., `parameters.py`, `sidebar.py`)
- Service modules: `{service_name}.py` (e.g., `ai_chat.py`, `session_state.py`)
- Utility modules: `{domain}_{utility}.py` (e.g., `sans_analysis_utils.py`)

**Directories:**
- `components/`: UI rendering modules
- `services/`: Business logic services
- `data/`: Non-code resources (data files, assets)
- `tests/`: Test suite parallel to src

**Functions:**
- `render_*()`: UI rendering functions (Streamlit side effects)
- `apply_*()`: State mutation functions
- `get_*()`: Getter/accessor functions
- `suggest_*()`: Heuristic/AI functions
- `analyze_*()`: Data analysis functions
- `create_*()`: Factory/constructor functions
- `init_*()`: Initialization functions

**Variables:**
- `st.session_state.{var_name}`: Session state keys use snake_case
- `{param_name}`: Parameter names come from sans-fitter model
- `param_updates`: Dictionary of ParamUpdate TypedDicts
- `fit_result`: FitResult TypedDict from fitting

**Types:**
- TypedDicts: PascalCase (e.g., ParamInfo, FitResult, ParamUpdate)
- Imports: from typing import TypedDict, Optional, cast (modern type hints)

## Where to Add New Code

**New Feature (e.g., new UI section):**
- Primary code: `src/sans_webapp/components/{feature}.py` (new component module)
- Service logic: `src/sans_webapp/services/{feature}.py` (if complex)
- Constants: Add to `src/sans_webapp/ui_constants.py`
- Types: Add to `src/sans_webapp/sans_types.py` if TypedDict needed
- Orchestration: Update `src/sans_webapp/app.py` to call new `render_*()` function

**New Component/Module:**
- Pure Streamlit rendering: `src/sans_webapp/components/{name}.py`
- Business logic: `src/sans_webapp/services/{name}.py`
- Domain logic (no UI): `src/sans_webapp/{domain}_{utility}.py`
- External API wrapper: `src/sans_webapp/{api}_client.py`

**Utilities/Helpers:**
- SANS analysis: Add to `src/sans_webapp/sans_analysis_utils.py`
- Session management: Add to `src/sans_webapp/services/session_state.py`
- UI constants: Add to `src/sans_webapp/ui_constants.py`
- Type definitions: Add to `src/sans_webapp/sans_types.py`

**Tests:**
- New feature tests: `tests/test_{feature}.py`
- Test helpers: `tests/conftest.py` (pytest fixtures, if needed)
- Naming: `test_*.py` files, `test_*()` functions, `Test*` classes

**Adding to Sidebar:**
- Add `render_*()` function in `src/sans_webapp/components/sidebar.py`
- Call from `main()` in `src/sans_webapp/app.py`
- Add strings to `src/sans_webapp/ui_constants.py`

**Adding to Main Content Area:**
- Create new component in `src/sans_webapp/components/{name}.py`
- Add `render_*()` function
- Call from `main()` in `src/sans_webapp/app.py` in appropriate column
- Add strings to `src/sans_webapp/ui_constants.py`

## Special Directories

**src/sans_webapp.egg-info/:**
- Purpose: Package metadata (generated by setuptools)
- Generated: Yes
- Committed: No (in .gitignore)

**tests/__pycache__/, src/sans_webapp/__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No (in .gitignore)

**.ruff_cache/, .pytest_cache/:**
- Purpose: Tool caches (ruff linter, pytest)
- Generated: Yes
- Committed: No (in .gitignore)

**C:\Users\piotr\projects\ai\SANS-webapp\.planning/**
- Purpose: GSD planning and analysis documents
- Generated: By GSD agent
- Committed: Yes

## Import Structure

**Session State Access Pattern:**
```python
# From any component or service
import streamlit as st
fitter = st.session_state.fitter
data_loaded = st.session_state.data_loaded
```

**Component Import Pattern (from app.py):**
```python
from sans_webapp.components.sidebar import render_data_upload_sidebar
from sans_webapp.components.parameters import render_parameter_configuration
from sans_webapp.services.session_state import init_session_state
```

**Constants Import Pattern:**
```python
from sans_webapp.ui_constants import APP_TITLE, UPLOAD_LABEL, etc
```

**Type Imports Pattern:**
```python
from sans_webapp.sans_types import FitResult, ParamInfo, ParamUpdate
```

## Module Re-exports

**In src/sans_webapp/__init__.py:**
- Exports for backwards compatibility: `get_all_models`, `analyze_data_for_ai_suggestion`, `suggest_models_ai`, etc.
- Allows: `from sans_webapp import get_all_models` instead of internal path

**In src/sans_webapp/app.py:**
- Re-exports for backwards compatibility from sans_analysis_utils and services
- Allows: `from sans_webapp.app import suggest_models_ai`

---

*Structure analysis: 2026-02-04*
