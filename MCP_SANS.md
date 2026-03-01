## Plan: MCP Server for SANS-webapp AI Assistant

### TL;DR

Add an embedded FastMCP server to SANS-webapp that exposes SANS-fitter functionality as MCP tools. Replace the current OpenAI-based chat with Anthropic Claude (which has native MCP support) to enable the AI to directly invoke tools like `set-model`, `set-parameter`, `run-fit`, and `enable-polydispersity`. Tools will mutate `st.session_state`, but only when a global "AI tools enabled" toggle is on. Tool-triggered UI refreshes should be staged via a rerun flag rather than calling `st.rerun()` inside tool handlers. The architecture mirrors SANS-pilot's FastMCP pattern but operates in-process with the Streamlit app.

### Steps

**1. Add dependencies to `pyproject.toml`** ✅ DONE
- Add `fastmcp` for MCP server implementation
- Add `anthropic` for Claude API client
- Add `mcp` SDK if needed for client integration within Streamlit

**2. Create MCP server module at `src/sans_webapp/mcp_server.py`** ✅ DONE
- Import `FastMCP` from `fastmcp`
- Copy tool decoration pattern from [main.py](src/sans_pilot/main.py) in SANS-pilot
- Define server with name `"sans-webapp-mcp"` and instructions describing SANS fitting capabilities

**3. Implement MCP tools matching SANS-pilot tools + webapp-specific actions** ✅ DONE

| Tool Name | Description | State Effect |
|-----------|-------------|--------------|
| `list-sans-models` | List available sasmodels | None |
| `get-model-parameters` | Get params for a model | None |
| `set-model` | Load a model into fitter | Updates `st.session_state.fitter`, `current_model`, `model_selected` |
| `set-parameter` | Set param value/bounds/vary | Updates fitter params in session_state |
| `set-multiple-parameters` | Batch param updates | Updates fitter params in session_state |
| `enable-polydispersity` | Enable PD for a param | Updates fitter PD settings |
| `set-structure-factor` | Add structure factor | Updates fitter SF settings |
| `remove-structure-factor` | Remove structure factor | Updates fitter SF settings |
| `run-fit` | Execute fitting | Queues background fit, updates `fit_status` |
| `get-fit-results` | Return current fit results | None (read-only) |
| `get-current-state` | Return full fitter state summary | None (read-only) |

Each state-modifying tool will:
1. Access `st.session_state.fitter` directly (passed via closure or global reference)
2. Call appropriate `SANSFitter` methods
3. Update relevant session_state flags
4. Return confirmation text for Claude to relay to user

Gate all state mutations behind a global toggle (e.g., `st.session_state.ai_tools_enabled`). If the toggle is off, tools should return a consistent "tools disabled" response without mutating state.

**4. Create Claude MCP client at `src/sans_webapp/services/claude_mcp_client.py`** ✅ DONE
- Replace current `openai_client.py` usage
- Use Anthropic SDK with MCP tool-use capability
- Configure MCP tool schemas from the embedded server
- Handle tool invocation round-trips natively

**5. Modify `services/ai_chat.py`** ✅ DONE
- Replace `create_chat_completion()` with Claude MCP-enabled chat
- Keep context-building logic from current `_build_context()` 
- Process tool calls and apply results to state
- After any state-modifying tool, set a rerun flag (e.g., `st.session_state.needs_rerun = True`) and trigger `st.rerun()` once in the main UI cycle

**6. Update `components/sidebar.py` chat UI** ✅ DONE
- Keep existing chat interface (text input, history display)
- Add an "AI tools enabled" toggle (global on/off)
- Add indicator when AI is invoking tools
- Potentially show tool invocation status (e.g., "Setting model to sphere...")
- Handle streaming responses if supported

**7. Create session-state bridge for MCP tools at `src/sans_webapp/services/mcp_state_bridge.py`** ✅ DONE
- Provide typed accessors for `get_fitter()`, `get_session_state()`
- Ensure thread-safety if MCP runs in separate thread (queue mutations for main thread)
- Handle edge cases: no data loaded, no model selected, etc.

**8. Update `app.py` initialization** ✅ DONE
- Initialize MCP server on app startup (once per session)
- Register MCP tools with state references
- Set up Claude client with API key (from session_state or env)

> Status: Implemented. `app.py` now assigns the current `SANSFitter` and `st.session_state` to the embedded MCP server using `set_fitter()` and `set_state_accessor()`. The Claude MCP client is pre-warmed at startup when an Anthropic API key is present (from `st.session_state.chat_api_key` or `ANTHROPIC_API_KEY`). Initialization errors are stored in `st.session_state.ai_client_error` and do not block UI startup.

**9. Add environment configuration** ✅ DONE
- `ANTHROPIC_API_KEY` env var for Claude API
- Update `.env` template and documentation
- Consider API key input in sidebar (like current `chat_api_key`)

> Status: Implemented. Added `.env.template` with example keys and updated `WEBAPP_README.md` to document `ANTHROPIC_API_KEY` usage (env var and `.env` file examples). Unit tests verify the template exists and `init_mcp_and_ai()` will use `ANTHROPIC_API_KEY` from the environment when `st.session_state.chat_api_key` is not present.

**10. Update types in `sans_types.py`** ✅ DONE
- Add `MCPToolResult` TypedDict for standardized tool responses
- Add `ChatMessage` type with tool invocation support

> Status: Implemented. Added `MCPToolResult` and `ChatMessage` TypedDicts to `src/sans_webapp/sans_types.py`. Added unit tests in `tests/test_sans_types.py` to validate the structures.

### File Structure (New/Modified)

```
src/sans_webapp/
├── mcp_server.py          # NEW: FastMCP server with tools
├── openai_client.py       # DEPRECATED or kept for fallback
├── services/
│   ├── ai_chat.py         # MODIFIED: Use Claude + MCP
│   ├── claude_mcp_client.py  # NEW: Anthropic MCP client
│   └── mcp_state_bridge.py   # NEW: Session state accessors
├── components/
│   └── sidebar.py         # MODIFIED: Tool status indicators
└── app.py                 # MODIFIED: Initialize MCP server
```

### Tool Implementation Example

Model the tools on [main.py](C:\projects\ai\SANS-pilot\src\sans_pilot\main.py) pattern:

```python
@mcp.tool(name="set-model", description="Load a SANS model (e.g., 'sphere', 'cylinder')")
def set_model(model_name: str) -> str:
    fitter = get_fitter()
    fitter.set_model(model_name)
    st.session_state.current_model = model_name
    st.session_state.model_selected = True
    return f"Model '{model_name}' loaded. Parameters: {list(fitter.params.keys())}"
```

### User Flow Example

**User says:** "Use sphere model with this dataset"

1. Claude receives message + sees available tools
2. Claude decides to call `set-model` with `model_name="sphere"`
3. MCP server executes tool, updates session_state
4. Tool returns confirmation: "Model 'sphere' loaded. Parameters: ['radius', 'sld', ...]"
5. Claude responds: "I've loaded the sphere model. The available parameters are..."
6. UI triggers rerun, right pane shows sphere model parameters

### Strategies

**AI tools enabled toggle**
- Store the toggle in `st.session_state.ai_tools_enabled` and default to `False`
- Gate all tool handlers: if disabled, return a standardized response and do nothing
- Show the toggle near the chat input so it is visible and discoverable

**Background fit queue**
- Create a `fit_queue` and `fit_status` in session state (`idle`, `queued`, `running`, `failed`, `completed`)
- `run-fit` enqueues a job with a unique id and returns immediately
- A background worker (thread or async task) processes the queue and updates `fit_result`, `fit_status`, and `fit_error`
- UI polls status each rerun and shows progress or final results

### Verification

- **Unit tests**: Add tests for MCP tools in [tests/](tests/) folder, mocking session_state ✅ DONE
  - `tests/test_mcp_tools.py` - Tests for MCP server tools, schemas, and state bridge
  - `tests/test_ai_chat.py` - Tests for AI chat service
  - `tests/test_sidebar_ai_chat.py` - Tests for sidebar UI components
  - `tests/conftest.py` - Shared fixtures (MockSessionState, MockFitter)
- **Integration test**: Manual flow through chat → tool invocation → UI update
- **Regression test**: Ensure existing UI controls still work alongside AI
- **Test command**: `pytest tests/ -v`
- **Manual check**: Type "use sphere model" in chat, verify parameters appear in right pane

### Decisions

- **Claude over OpenAI**: Native MCP tool support simplifies integration vs OpenAI function-calling adapter
- **Embedded over separate service**: Avoids network overhead, direct session_state access
- **Direct mutation over events**: Simpler implementation, matches existing Streamlit patterns
- **Mirroring SANS-pilot tools**: Consistency across projects, proven patterns
