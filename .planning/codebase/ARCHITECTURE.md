# Architecture

**Analysis Date:** 2026-02-05

## Pattern Overview

**Overall:** Streamlit-based layered MVC with AI-powered assistant capabilities

**Key Characteristics:**
- Streamlit framework for interactive web UI
- Clear separation between UI components, business logic, and services
- MCP (Model Context Protocol) server for AI tool integration
- Session state management for stateful UI interactions
- Pluggable AI backends (OpenAI fallback, Anthropic Claude primary)

## Layers

**Presentation Layer (UI Components):**
- Purpose: Render interactive UI elements and handle user input
- Location: `src/sans_webapp/components/`
- Contains: `sidebar.py`, `parameters.py`, `data_preview.py`, `fit_results.py`
- Depends on: Services layer, UI constants, Streamlit
- Used by: Main app orchestration in `app.py`

**Services Layer (Business Logic):**
- Purpose: Implement application logic independent of UI framework
- Location: `src/sans_webapp/services/`
- Contains: `session_state.py`, `ai_chat.py`, `claude_mcp_client.py`, `mcp_state_bridge.py`
- Depends on: SANSFitter, AI client libraries, sans_analysis_utils
- Used by: Components and main app

**MCP Integration Layer:**
- Purpose: Provide AI tool interface for Claude to interact with fitter
- Location: `src/sans_webapp/mcp_server.py`, `src/sans_webapp/services/claude_mcp_client.py`
- Contains: FastMCP tool definitions, tool handler mappings, MCP client
- Depends on: SANSFitter, fastmcp, Anthropic SDK
- Used by: AI chat service for Claude tool invocation

**Analysis Utilities:**
- Purpose: Shared, framework-agnostic analysis functions
- Location: `src/sans_webapp/sans_analysis_utils.py`
- Contains: Data analysis, model suggestions, plotting functions
- Depends on: NumPy, Plotly, SANSFitter
- Used by: Components, services, and can be used by CLI tools

**Type Definitions:**
- Purpose: Centralized type hints via TypedDict
- Location: `src/sans_webapp/sans_types.py`
- Contains: `ParamInfo`, `FitResult`, `ChatMessage`, `MCPToolResult`, `ParamUpdate`, `PDUpdate`
- Used by: All layers for type safety and IDE support

**Constants:**
- Purpose: Centralize all UI string constants
- Location: `src/sans_webapp/ui_constants.py`
- Contains: Labels, headers, help text, configuration values
- Used by: All UI components

## Data Flow

**Data Upload & Model Selection Flow:**

1. User uploads SANS data file via `render_data_upload_sidebar()` in `src/sans_webapp/components/sidebar.py`
2. File is loaded into `SANSFitter` instance stored in `st.session_state.fitter`
3. `data_loaded` flag set to True in session state
4. User selects model manually or via AI suggestions in `render_model_selection_sidebar()`
5. Model is loaded into fitter via `fitter.set_model(model_name)`
6. `model_selected` flag set to True

**Parameter Configuration Flow:**

1. `render_parameter_configuration()` in `src/sans_webapp/components/parameters.py` renders parameter widgets
2. User adjusts values via sliders/text inputs, stored with keys like `value_{param_name}`, `min_{param_name}`, `vary_{param_name}`
3. `render_parameter_configuration()` returns `param_updates: dict[str, ParamUpdate]`
4. Presets can be applied via `apply_pending_preset()`
5. Updates persist in session state for use during fitting

**Fitting Flow:**

1. User clicks "Run Fit" button in `render_fitting_sidebar()` in `app.py`
2. `apply_param_updates()` syncs UI state back to fitter
3. Polydispersity settings applied if enabled via `apply_pd_updates()`
4. `fitter.fit(engine, method)` executes fitting algorithm
5. Result stored in `st.session_state.fit_result` as `FitResult` TypedDict
6. `fit_completed` flag set to True
7. Fit results displayed by `render_fit_results()` in `src/sans_webapp/components/fit_results.py`

**AI Chat & MCP Tool Invocation Flow:**

1. User enters message in chat input in `render_ai_chat_column()` in `src/sans_webapp/components/sidebar.py`
2. Message sent to Claude via `send_chat_message()` in `src/sans_webapp/services/ai_chat.py`
3. Claude client created via `get_claude_client()` in `src/sans_webapp/services/claude_mcp_client.py`
4. If Claude requests tool use, message returned with tool_use blocks
5. Tool name mapped to handler in `_tool_handlers` dict from `mcp_server.py`
6. Tool handler executes (e.g., `set_model()`, `run_fit()`, `get_fit_results()`)
7. Tool result returned to Claude for continuation
8. Final response displayed in chat history in UI
9. MCP tools have access to fitter via `get_fitter()` and session state via `_state_accessor`

**State Management:**

- **Session State**: Streamlit's `st.session_state` serves as single source of truth
- **Initialization**: `init_session_state()` in `src/sans_webapp/services/session_state.py` sets defaults
- **Fitter**: Persistent `SANSFitter` instance across reruns (callable default instantiates on first run)
- **UI State**: Parameter values, visibility flags, expander states stored with prefixed keys
- **Fit Results**: Cached until new fit is run
- **Chat History**: Maintained in session state across reruns

## Key Abstractions

**SANSFitter:**
- Purpose: Encapsulates all SANS data fitting logic
- Examples: `st.session_state.fitter`
- Pattern: Dependency injection - passed to components/services that need it
- Methods: `load_data()`, `set_model()`, `set_param()`, `fit()`, `get_polydisperse_parameters()`

**TypedDict Structures:**
- Purpose: Type-safe dictionaries with IDE support
- Examples: `ParamInfo`, `FitResult`, `ChatMessage`, `ParamUpdate`
- Pattern: Used throughout for data contracts between layers

**Streamlit Session State:**
- Purpose: Persistent state across app reruns without database
- Pattern: Centralized initialization via `init_session_state()`
- Keys use consistent prefixes for organization (e.g., `value_`, `min_`, `vary_`, `pd_`)

**MCP Tool System:**
- Purpose: Standardized interface for AI to invoke backend actions
- Pattern: Tool name → function mapping in `claude_mcp_client._tool_handlers`
- Tools: `list-sans-models`, `get-model-parameters`, `set-model`, `set-parameter`, `run-fit`, etc.
- Abstraction: Claude sees tools as capabilities, not implementation details

## Entry Points

**Web Application:**
- Location: `src/sans_webapp/app.py` - `main()` function
- Triggers: `streamlit run src/sans_webapp/app.py` or via `sans-webapp` command
- Responsibilities: Page configuration, layout orchestration, sidebar rendering, main content rendering, MCP/AI initialization

**Command-Line:**
- Location: `src/sans_webapp/__main__.py`
- Triggers: `python -m sans_webapp`
- Responsibilities: Entry point delegation to Streamlit runner

**MCP Server:**
- Location: `src/sans_webapp/mcp_server.py` - FastMCP instance
- Triggers: Loaded by `claude_mcp_client.py` when Claude makes tool calls
- Responsibilities: Define available tools, handle tool invocation, provide fitter/state access

## Error Handling

**Strategy:** Try-catch with user-facing feedback via Streamlit messages

**Patterns:**

- **File Upload**: `render_data_upload_sidebar()` catches file parsing errors, displays `st.error()`
- **Model Selection**: `set_model()` MCP tool validates model exists, returns error string
- **Fitting**: `render_fitting_sidebar()` catches fit exceptions, displays `st.sidebar.error()`
- **AI Client**: `init_mcp_and_ai()` in `app.py` catches client creation errors, stores in `st.session_state.ai_client_error`, allows UI to continue
- **MCP Tools**: Tools return error strings for Claude to interpret
- **Chat**: `send_chat_message()` returns error message if API key missing or API fails
- **Parameter Validation**: `apply_param_updates()` validates bounds before applying

## Cross-Cutting Concerns

**Logging:** Uses Python `print()` statements and Streamlit's built-in logging for debugging; no structured logging framework

**Validation:**
- Parameter bounds checked before fitting
- Model names validated against available models from `get_all_models()`
- Data file format validated during upload (CSV/DAT with Q, I, dI columns)
- API keys checked before attempting AI operations

**Authentication:**
- Optional Anthropic API key stored in session state
- Claude MCP tools check `_check_tools_enabled()` to respect user intent
- No persistent authentication; per-session only

**UI Responsiveness:**
- Spinners displayed during long operations (fitting, AI suggestions)
- Parameter widgets use session state keys to persist across reruns
- Sidebar expanders use session state flags to maintain expansion state

---

*Architecture analysis: 2026-02-05*
