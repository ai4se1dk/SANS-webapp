# Architecture

**Analysis Date:** 2026-02-04

## Pattern Overview

**Overall:** Layered MVC-style architecture with separation of concerns between UI rendering, business logic, and data management.

**Key Characteristics:**
- Streamlit-based reactive frontend with stateful session management
- Domain service layer (ai_chat, session_state) for business logic
- UI component layer with rendering functions
- Utility/helper functions isolated from UI framework
- Type-safe data contracts via TypedDicts
- SANSFitter from external sans-fitter package as core data model

## Layers

**UI Layer (Components):**
- Purpose: Render Streamlit UI elements and handle user interactions
- Location: `src/sans_webapp/components/`
- Contains: `sidebar.py`, `data_preview.py`, `fit_results.py`, `parameters.py`
- Depends on: services layer, sans_types, ui_constants
- Used by: `app.py` (main orchestrator)
- Pattern: Pure rendering functions that accept data and return void (side effects via st.* calls)

**Services Layer (Business Logic):**
- Purpose: Handle application logic, AI integration, state management
- Location: `src/sans_webapp/services/`
- Contains: `ai_chat.py`, `session_state.py`
- Depends on: sans_types, sans_analysis_utils, openai_client, sans-fitter
- Used by: components, app.py
- Pattern: Pure functions with side effects limited to session state mutations and API calls

**Utilities Layer (Domain Logic):**
- Purpose: SANS-specific analysis and data processing without UI dependencies
- Location: `src/sans_webapp/`
- Contains: `sans_analysis_utils.py`, `openai_client.py`
- Depends on: numpy, scipy, plotly, sans-fitter
- Used by: services, components
- Pattern: Pure functions that can be used independently of Streamlit

**Data/Configuration Layer:**
- Purpose: Type definitions and UI constants
- Location: `src/sans_webapp/sans_types.py`, `src/sans_webapp/ui_constants.py`
- Contains: TypedDicts for type safety, string constants for UI text
- Depends on: none (only typing module)
- Used by: all other layers

**Entry Point:**
- Location: `src/sans_webapp/app.py` (main Streamlit app)
- Location: `src/sans_webapp/__main__.py` (CLI entry point)

## Data Flow

**1. Data Upload & Model Loading Flow:**

1. User selects file via `render_data_upload_sidebar()` (components/sidebar.py)
2. File written to temporary location
3. SANSFitter instance loads data via `fitter.load_data(path)`
4. `session_state.data_loaded` set to True
5. Sidebar UI expands model selection section
6. User selects model (Manual or AI-Assisted)
7. If AI-assisted: `suggest_models_ai()` calls OpenAI API
8. User loads model: `fitter.set_model(name)` + `session_state.model_selected = True`

**2. Parameter Configuration & Fitting Flow:**

1. User modifies parameters in `render_parameter_configuration()` (components/parameters.py)
2. Parameter changes stored in session state (value_*, min_*, max_*, vary_* keys)
3. User clicks "Run Fit" button
4. `render_fitting_sidebar()` applies current parameters via `apply_param_updates(fitter, updates)`
5. Fitting engine selected (bumps/lmfit) with method
6. `fitter.fit(engine=engine, method=method)` executed
7. Results stored in `session_state.fit_result`
8. `render_fit_results()` displays chi-squared and fitted parameters

**3. AI Chat Flow:**

1. User sends message via `render_ai_chat_column()` (components/sidebar.py)
2. Message added to `session_state.chat_history`
3. `send_chat_message(user_message, api_key, fitter)` called (services/ai_chat.py)
4. System message built with current data/model/fit context
5. OpenAI API called via `create_chat_completion()` (openai_client.py)
6. Response added to chat_history
7. Streamlit reruns and displays updated chat

**State Management:**

- Session state initialized in `init_session_state()` (services/session_state.py)
- Core state: `fitter`, `data_loaded`, `model_selected`, `fit_completed`
- UI state: `expand_data_upload`, `expand_model_selection`, `expand_fitting`
- Parameter state: `value_{param}`, `min_{param}`, `max_{param}`, `vary_{param}`
- Chat state: `chat_history`, `chat_api_key`
- Expander states control which sections are visible on page load
- Parameter updates collected during render, applied on button click

## Key Abstractions

**SANSFitter:**
- Purpose: Encapsulates SANS data and fitting model from sans-fitter package
- Examples: Created in session_state, accessed via `st.session_state.fitter` throughout
- Pattern: Central stateful object updated via `set_model()`, `load_data()`, `fit()`, `set_param()`
- Responsible for: data loading, model management, parameter management, fitting execution

**ParamUpdate (TypedDict):**
- Purpose: Type-safe representation of parameter changes
- Pattern: Used to collect UI inputs and pass to `apply_param_updates()` in components/parameters.py
- Structure: value, min, max, vary (all required)

**FitResult (TypedDict):**
- Purpose: Type-safe representation of fitting output
- Pattern: Returned from `fitter.fit()`, stored in session_state, passed to components
- Structure: chisq (goodness of fit), parameters dict with values and standard errors

**Component Rendering Functions:**
- Purpose: Pure functions that render UI without business logic
- Pattern: All named `render_*`, accept fitter or session state, return None
- Examples: `render_data_preview()`, `render_parameter_configuration()`, `render_fit_results()`

## Entry Points

**Web Application Entry:**
- Location: `src/sans_webapp/__main__.py`
- Triggers: `sans-webapp` command or `python -m sans_webapp`
- Responsibilities: Locates app.py, delegates to Streamlit CLI

**Main Streamlit App:**
- Location: `src/sans_webapp/app.py`
- Triggers: Streamlit server startup
- Responsibilities:
  - Initialize session state
  - Render sidebar (data upload, model selection, fitting)
  - Render two-column layout (main content + AI chat)
  - Orchestrate component rendering based on state
  - Inject custom CSS/JS for resizable columns

**Component Rendering Chain (from app.py):**
- `init_session_state()` → initialize
- `render_data_upload_sidebar()` → file upload
- `render_model_selection_sidebar()` → model choice
- `render_ai_chat_column()` → AI assistant (right column)
- `render_data_preview()` → plot + statistics
- `render_parameter_configuration()` → parameter inputs
- `render_fitting_sidebar()` → fitting controls + Run button
- `render_fit_results()` → results display

## Error Handling

**Strategy:** Try-except blocks at service boundaries with user-facing error messages

**Patterns:**
- File upload errors caught in `render_data_upload_sidebar()`, shown via `st.error()`
- Model loading errors caught in `render_model_selection_sidebar()`, shown via `st.error()`
- Fitting errors caught in `render_fitting_sidebar()`, shown via `st.sidebar.error()`
- AI API errors caught in `send_chat_message()` and `suggest_models_ai()`, shown via `st.warning()` or return error message
- Parameter validation: warnings if no parameters marked as "vary" before fitting

**API Error Handling:**
- OpenAI API calls wrapped in try-except in `openai_client.py`
- Fallback to simple heuristic if AI suggestion fails (suggest_models_simple)
- Missing API key returns warning message instead of crashing

## Cross-Cutting Concerns

**Logging:** Console output via `print()` for startup, errors handled via st.error/st.warning

**Validation:**
- File upload: check for .csv/.dat extension
- Parameters: check that at least one parameter has vary=True before fitting
- API key: validate presence before calling OpenAI

**Authentication:**
- OpenAI API key: user-provided via text input, stored in session_state.chat_api_key
- No persistent auth; key cleared on session reset

**Session Persistence:**
- Session state lost on page refresh or new browser session
- Data files written to temp directory, cleaned up after load
- No database persistence (single-session analysis tool)

---

*Architecture analysis: 2026-02-04*
