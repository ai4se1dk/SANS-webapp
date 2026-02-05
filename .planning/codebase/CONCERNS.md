# Codebase Concerns

**Analysis Date:** 2026-02-05

## Tech Debt

**Duplicate initialization call in app.py:**
- Issue: `init_mcp_and_ai()` is called twice on lines 290 and 293 in `src/sans_webapp/app.py`
- Files: `src/sans_webapp/app.py` (lines 290, 293)
- Impact: Redundant initialization may cause unnecessary API key validation attempts and client creation; wastes CPU cycles
- Fix approach: Remove one of the duplicate calls (line 293)

**Silent exception handling with pass statements:**
- Issue: Multiple `except` blocks catch exceptions and silently pass without logging, notably in `src/sans_webapp/components/fit_results.py` line 95: `except Exception: pass  # Silently skip residual stats if calculation fails`
- Files: `src/sans_webapp/components/fit_results.py` (line 95), `src/sans_webapp/services/ai_chat.py` (line 84), `src/sans_webapp/components/sidebar.py` (lines 344, 394)
- Impact: Errors are completely hidden, making debugging difficult; users see incomplete results without knowing why
- Fix approach: Replace with proper error logging using Python's `logging` module; show user-facing warnings for non-critical failures

**Global mutable state in MCP server:**
- Issue: `src/sans_webapp/mcp_server.py` uses global variables `_fitter` and `_state_accessor` (lines 43-44) that are set and modified by various functions
- Files: `src/sans_webapp/mcp_server.py` (lines 43-44, 47-56)
- Impact: Creates thread-safety issues in multi-user scenarios; state mutations are not tracked; difficult to test in isolation
- Fix approach: Refactor to use dependency injection or a singleton pattern with proper locking for concurrent access

**Broad exception catching without discrimination:**
- Issue: Multiple locations catch generic `Exception` instead of specific exception types (`except Exception as e:`)
- Files: `src/sans_webapp/mcp_server.py` (multiple lines), `src/sans_webapp/services/ai_chat.py` (lines 117, 240, 312), `src/sans_webapp/components/sidebar.py` (lines 112, 138, 223)
- Impact: Masks real errors; makes it impossible to distinguish between expected errors and programming bugs
- Fix approach: Catch specific exception types (ValueError, FileNotFoundError, RuntimeError, etc.); only catch Exception as last resort with clear comments

**Hardcoded model name in claude_mcp_client.py:**
- Issue: Model is hardcoded as `"claude-sonnet-4-20250514"` on line 284 of `src/sans_webapp/services/claude_mcp_client.py`
- Files: `src/sans_webapp/services/claude_mcp_client.py` (line 284)
- Impact: Cannot easily switch models; outdated model version becomes unmaintainable; no fallback if model is deprecated
- Fix approach: Move to configuration/environment variable with sensible default

**Temporary files not cleaned up on all error paths:**
- Issue: `src/sans_webapp/components/sidebar.py` creates temporary files with `tempfile.NamedTemporaryFile` (line 123) but cleanup only happens on success path; exception on line 138 could leave temp files
- Files: `src/sans_webapp/components/sidebar.py` (lines 123-135)
- Impact: Disk space leaks accumulate over time; could eventually cause storage issues
- Fix approach: Use context manager (`with tempfile.NamedTemporaryFile(...) as tmp_file:`) or ensure cleanup in finally block

## Known Bugs

**Duplicate return statement in ai_chat.py:**
- Symptoms: Function `send_chat_message_with_tools()` has return statement on line 435 after already returning on line 433
- Files: `src/sans_webapp/services/ai_chat.py` (lines 433, 435)
- Trigger: When function completes normally
- Workaround: Code is unreachable but doesn't cause runtime error; dead code can confuse future maintainers

**Unsafe html rendering without proper escaping:**
- Symptoms: CSS and JavaScript injected directly into Streamlit with `unsafe_allow_html=True` on line 282
- Files: `src/sans_webapp/app.py` (lines 181-283, specifically line 282)
- Trigger: Any malicious input to the session state could execute arbitrary JavaScript
- Workaround: Currently no input validation on the CSS/JS being injected

**Potential None dereference in DirectModel initialization:**
- Symptoms: `src/sans_webapp/components/fit_results.py` line 56 calls `DirectModel(fitter.data, fitter.kernel)` without null checks after checking `fitter.data` but not `fitter.kernel`
- Files: `src/sans_webapp/components/fit_results.py` (lines 56-57, 90)
- Trigger: When a model is selected but kernel is not properly initialized
- Workaround: Caught by exception handler that silently swallows error

**Session state key inconsistencies:**
- Symptoms: Session state uses inconsistent key naming: `fit_result` vs `fit_completed` vs `needs_rerun`; some keys optional, others not checked before access
- Files: Multiple files including `src/sans_webapp/app.py`, `src/sans_webapp/components/fit_results.py`, `src/sans_webapp/services/ai_chat.py`
- Trigger: When session state is not fully initialized or corrupted
- Workaround: Use `.get()` with defaults everywhere instead of direct access

## Security Considerations

**API keys exposed in memory and logs:**
- Risk: Anthropic and OpenAI API keys stored in `st.session_state.chat_api_key` persist in memory; may appear in error logs or crash dumps
- Files: `src/sans_webapp/components/sidebar.py` (line 173), `src/sans_webapp/app.py` (line 89), `src/sans_webapp/services/session_state.py` (line 22)
- Current mitigation: Text input marked as `type='password'` in UI; environment variables prefer reads over session storage
- Recommendations:
  - Never log API keys (add check in error handlers)
  - Clear API keys from memory after use
  - Use environment variables exclusively (ANTHROPIC_API_KEY, not session_state)
  - Implement API key rotation/expiration logic

**Unsafe string formatting in error messages:**
- Risk: User input and file names are concatenated directly into error messages without sanitization
- Files: `src/sans_webapp/components/sidebar.py` (line 113, 139), `src/sans_webapp/app.py` (line 165)
- Current mitigation: Streamlit's error() function escapes HTML, but could expose internal paths or data structures
- Recommendations: Strip sensitive information from error messages shown to users; log full errors separately

**No input validation on tool invocations:**
- Risk: MCP tools accept arbitrary parameter values without range checking or type validation
- Files: `src/sans_webapp/mcp_server.py` (tools accept raw float/string inputs), `src/sans_webapp/services/claude_mcp_client.py` (line 254 execute_tool does no validation)
- Current mitigation: Sans-fitter library may have bounds checking, but not guaranteed
- Recommendations: Validate parameter ranges before executing tools; whitelist allowed model names; implement rate limiting on fit operations

**Environment variable reads without defaults:**
- Risk: `__import__('os').environ.get('ANTHROPIC_API_KEY')` on line 89 of `src/sans_webapp/app.py` uses dynamic import which could be manipulated
- Files: `src/sans_webapp/app.py` (line 89)
- Current mitigation: Uses `os.environ.get()` safely with fallback to None
- Recommendations: Use standard `import os` at module level; avoid dynamic imports for security-critical paths

## Performance Bottlenecks

**DirectModel calculation on every render:**
- Problem: `src/sans_webapp/components/fit_results.py` (lines 56-57) recalculates fit curve on every Streamlit rerun; expensive for large datasets
- Files: `src/sans_webapp/components/fit_results.py` (lines 56-57, 90-91), `src/sans_webapp/services/ai_chat.py` (lines 75-77)
- Cause: No caching of calculated fit values; called in rendering paths that execute on every interaction
- Improvement path: Cache fit results in session state with model/parameter hash key; invalidate only when model or params change

**Inefficient polydispersity parameter enumeration:**
- Problem: Multiple loops iterate through polydispersity parameters independently in `src/sans_webapp/components/fit_results.py` (lines 148-158) and `src/sans_webapp/components/parameters.py`
- Files: `src/sans_webapp/components/fit_results.py` (lines 148-158), `src/sans_webapp/components/parameters.py` (multiple polydispersity sections)
- Cause: No memoization of polydispersity parameter lists; repeated calls to `fitter.get_polydisperse_parameters()`
- Improvement path: Cache PD parameter list during session; only recalculate when model changes

**AI chat context building unbounded:**
- Problem: `src/sans_webapp/services/ai_chat.py` (lines 40-99) builds large context strings with full data samples without limits
- Files: `src/sans_webapp/services/ai_chat.py` (lines 73-83 sample 50 data points every call)
- Cause: Context includes full conversation history and data traces that grow unbounded
- Improvement path: Implement context window management; limit conversation history depth; sample data intelligently

**Temporary file creation on every data upload:**
- Problem: `src/sans_webapp/components/sidebar.py` (line 123) creates new temp file for each upload even if same file is re-uploaded
- Files: `src/sans_webapp/components/sidebar.py` (lines 117-136)
- Cause: Check `last_uploaded_file_id` on line 120 has race condition; temp file created before check in line 123
- Improvement path: Move file write after file ID check; use proper temp file caching

## Fragile Areas

**Parameter slider state management:**
- Files: `src/sans_webapp/components/fit_results.py` (lines 169-243)
- Why fragile: Complex interaction between `prev_selected_param`, `slider_value`, and session state keys; multiple conditional branches (lines 201-225); slider value persistence is error-prone
- Safe modification: Add comprehensive tests for parameter switching; document session key contract; consider moving state logic to service layer
- Test coverage: No unit tests for slider state transitions; manual testing required

**MCP tool execution without state validation:**
- Files: `src/sans_webapp/mcp_server.py` (lines 188-400+)
- Why fragile: Tools modify fitter and session state without pre/post condition validation; assume fitter is always initialized (line 200 `fitter.set_model()` could fail if fitter is incompletely initialized)
- Safe modification: Add guards that check fitter completeness; implement state snapshots before mutations; add rollback capability
- Test coverage: Tests in `tests/test_mcp_tools.py` exist but may not cover all state mutation paths

**AI chat conversation history management:**
- Files: `src/sans_webapp/services/ai_chat.py` (lines 277-292), `src/sans_webapp/components/sidebar.py` (chat rendering section ~lines 280-400)
- Why fragile: Conversation history stored in session state without size limits; list grows indefinitely; serialization/deserialization of messages could fail
- Safe modification: Implement conversation window (last N messages); add persistence layer; validate message format on read
- Test coverage: Mock chat history in tests, but no integration tests with real long-running conversations

**Example data path resolution:**
- Files: `src/sans_webapp/components/sidebar.py` (lines 62-84)
- Why fragile: Multi-fallback path resolution (package resources, CWD, parent directories) is unpredictable in different deployment contexts
- Safe modification: Single explicit path from environment variable or configuration; fail loudly if not found
- Test coverage: Path resolution tested with mocks but not in real package deployments

**Component exception handlers swallowing errors:**
- Files: `src/sans_webapp/components/fit_results.py` (line 70-71, 94-95), `src/sans_webapp/components/sidebar.py` (lines 112-113, 138-139, 223)
- Why fragile: Each component independently catches and displays errors; duplicated error handling logic; inconsistent error messages
- Safe modification: Centralize error handling in error boundary component; ensure all exceptions are logged
- Test coverage: Tests do not verify exception handling paths

## Scaling Limits

**Session state memory usage:**
- Current capacity: `st.session_state` holds all data for single user session (fitter, chat history, parameters, uploaded data)
- Limit: Unlimited growth until server runs out of memory; no cleanup on session timeout
- Scaling path: Implement session expiration (30-60 min idle); use persistent storage for chat history; implement garbage collection on large fitter objects

**Concurrent API calls to Claude/OpenAI:**
- Current capacity: Single `ClaudeMCPClient` instance per session; calls block on `client.messages.create()`
- Limit: Server can handle N concurrent users × M tokens per request; no queuing or rate limiting
- Scaling path: Implement token budget system; queue long-running requests; use async/await for API calls; add request timeouts

**SANSFitter object persistence:**
- Current capacity: One fitter per session held in memory indefinitely
- Limit: Complex fitter objects with large datasets consume 10-100MB per session; scaling to 100+ users requires 1-10GB RAM
- Scaling path: Move fitter to disk cache with session ID key; implement LRU eviction; use processes for fitting operations

## Dependencies at Risk

**sans-fitter version pinning:**
- Risk: Depends on `sans-fitter>=0.0.3` (line 29 of `pyproject.toml`) with loose version constraint; API could change
- Impact: Major version bump could break parameter access patterns (`fitter.params`, `fitter.set_model()`)
- Migration plan: Pin to specific version `sans-fitter==0.0.X`; monitor releases for breaking changes; create integration tests for fitter API

**sasmodels version compatibility:**
- Risk: `sasmodels>=1.0` could introduce model changes or removal
- Impact: Model names suggested by AI could become invalid; parameter sets could change
- Migration plan: Maintain list of tested model names; add version check in app startup; vendor model definitions if needed

**Streamlit version lock:**
- Risk: `streamlit>=1.28.0` could break on major version (2.0); session_state API may change
- Impact: UI components may not render; state management could fail
- Migration plan: Test against latest Streamlit monthly; pin major version `streamlit>=1.28,<2` if needed

**Claude model deprecation:**
- Risk: `claude-sonnet-4-20250514` hardcoded (line 284 of `src/sans_webapp/services/claude_mcp_client.py`) will be deprecated
- Impact: App will stop working once model is removed; no fallback
- Migration plan: Make model configurable via environment variable; implement model discovery via Anthropic API

## Missing Critical Features

**No persistent storage for fit results:**
- Problem: Fit results only live in `st.session_state`; lost when session expires or browser closes
- Blocks: Cannot review past fits; cannot export results for publication; no audit trail
- Recommended: Add SQLite/PostgreSQL backend for results; implement export to HDF5/MATLAB formats

**No role-based access control:**
- Problem: No user authentication; all sessions have same permissions; sensitive fitting operations unrestricted
- Blocks: Cannot enforce policies; cannot audit who did what; multi-tenant deployment impossible
- Recommended: Add auth0 or similar OAuth2 provider; implement permission checks in MCP tools

**No data validation schema:**
- Problem: Uploaded CSV files accepted with no schema validation; could corrupt fitting if wrong column format
- Blocks: Users can accidentally load data in wrong format; no clear error messages
- Recommended: Define and enforce CSV schema; show preview of parsed data before loading

## Test Coverage Gaps

**AI chat tool invocation path:**
- What's not tested: End-to-end tool invocation with session state mutations (e.g., set model → run fit → retrieve results)
- Files: `src/sans_webapp/services/ai_chat.py` (lines 245-313), `src/sans_webapp/mcp_server.py` (entire file)
- Risk: Tools could silently fail to modify state; mutations could be out of sync with UI
- Priority: **High** - Tool invocations are critical path for AI features

**Parameter bounds enforcement:**
- What's not tested: Setting parameters with invalid bounds; min > max cases; NaN/Inf values
- Files: `src/sans_webapp/mcp_server.py` (lines 215-249), `src/sans_webapp/components/parameters.py` (parameter slider lines 227-236)
- Risk: Silent parameter clamping; fitting with invalid bounds
- Priority: **High** - Bad parameters cause failed fits with cryptic errors

**Polydispersity parameter state consistency:**
- What's not tested: Enabling/disabling polydispersity multiple times; switching models with different PD parameters; PD parameters in fit results
- Files: `src/sans_webapp/components/parameters.py` (polydispersity section), `src/sans_webapp/components/fit_results.py` (lines 148-158)
- Risk: Stale PD configuration; inconsistent model/PD state
- Priority: **Medium** - PD is optional feature but can cause silent failures

**Error recovery and retry logic:**
- What's not tested: Network failures during API calls; partial model loads; corrupted session state recovery
- Files: `src/sans_webapp/services/claude_mcp_client.py` (API calls), `src/sans_webapp/services/ai_chat.py` (suggest_models_ai fallback lines 240-242)
- Risk: Transient failures treated as permanent; no graceful degradation
- Priority: **Medium** - Important for production reliability

**Session state initialization edge cases:**
- What's not tested: Multiple rapid page reloads; session state access before init_session_state() completes; missing session state keys
- Files: `src/sans_webapp/services/session_state.py` (init_session_state function)
- Risk: AttributeError on missing keys; race conditions during initialization
- Priority: **Medium** - Could cause crashes on startup under load

---

*Concerns audit: 2026-02-05*
