# Codebase Concerns

**Analysis Date:** 2026-02-04

## Tech Debt

**API Key Storage in Session State:**
- Issue: API keys are stored in plaintext in Streamlit session state and passed through component functions
- Files: `src/sans_webapp/services/ai_chat.py`, `src/sans_webapp/components/sidebar.py` (lines 166-173)
- Impact: Sensitive credentials vulnerable to exposure if session data is logged or cached. No encryption or secure storage mechanism.
- Fix approach: Implement secure credential storage (environment variables only, never in session state). Add warning if API key is entered via UI that it should come from environment variables instead.

**Bare Exception Handling:**
- Issue: Multiple catch-all exception handlers that silently fail or return generic error messages
- Files: `src/sans_webapp/services/ai_chat.py` (line 84, 117), `src/sans_webapp/components/fit_results.py` (line 94-95), `src/sans_webapp/components/sidebar.py` (line 112, 138)
- Impact: Difficult to debug issues. Real errors masked. Data corruption or incorrect results go unnoticed.
- Fix approach: Use specific exception types. Log detailed errors to file for debugging. Only catch expected exceptions.

**Inline CSS/JavaScript in Streamlit App:**
- Issue: Complex resizable column UI implemented with hardcoded JavaScript and CSS selectors
- Files: `src/sans_webapp/app.py` (lines 146-249)
- Impact: Fragile implementation dependent on Streamlit's internal DOM structure. Breaks on Streamlit version updates. Selector targets `data-testid="stHorizontalBlock"` which could change.
- Fix approach: Use Streamlit's native layout features instead of DOM manipulation. If custom behavior needed, move to Streamlit component or custom theme.

**No Validation of Uploaded Data:**
- Issue: Data files accepted without format validation beyond file extension
- Files: `src/sans_webapp/components/sidebar.py` (lines 123-142)
- Impact: Invalid CSV files could crash the app or produce confusing errors. No guardrails for malformed data.
- Fix approach: Validate CSV structure, column names, numeric values, and data range before loading. Show specific error messages.

## Known Bugs

**Polydispersity UI State Inconsistency:**
- Symptoms: Session state for polydispersity can become stale when switching models. Form values don't update properly.
- Files: `src/sans_webapp/components/parameters.py` (lines 364-370)
- Trigger: Switch from one model to another model with different PD parameters, then try to adjust polydispersity settings
- Workaround: Manually clear session state or reload page. Code attempts to handle this at lines 366-370 but validation is incomplete.

**Temporary File Cleanup on Error:**
- Symptoms: Temporary files created during data upload may not be deleted if exception occurs between creation and cleanup
- Files: `src/sans_webapp/components/sidebar.py` (lines 123-135)
- Trigger: Upload file, then exception occurs after tempfile creation but before `os.unlink()`
- Workaround: Use context manager or try/finally to ensure cleanup. Currently only deletes on success path.

**Missing Test Coverage for Error Cases:**
- Symptoms: Only happy path tested in test suite
- Files: `tests/test_app.py` - most tests mock success cases
- Impact: Error handling code paths untested. Bugs in exception handling go undetected.
- Workaround: Run manual testing with invalid inputs

## Security Considerations

**OpenAI API Key Exposure:**
- Risk: API keys entered in web UI transmitted over network and stored in session state. Could be logged in browser console or network traffic.
- Files: `src/sans_webapp/components/sidebar.py` (lines 166-170), `src/sans_webapp/services/ai_chat.py` (line 105-113)
- Current mitigation: Streamlit marks input as `type='password'` for display, but data still stored insecurely in session state.
- Recommendations:
  - Move API key to environment variable only (e.g., `OPENAI_API_KEY`)
  - Remove UI input field for API key
  - Document in README that key must be set via environment variable
  - Add validation to fail gracefully if key missing from environment

**External API Calls Without Rate Limiting:**
- Risk: Unbounded calls to OpenAI API could result in unexpected charges or DoS vulnerability
- Files: `src/sans_webapp/services/ai_chat.py` (lines 105-113, 164-169)
- Current mitigation: None
- Recommendations:
  - Implement rate limiting (max calls per session/minute)
  - Add cost estimation warnings
  - Log all API calls with timestamps
  - Set hard limits on token consumption

**Temporary File Path Disclosure:**
- Risk: Temp files created with predictable names during upload
- Files: `src/sans_webapp/components/sidebar.py` (line 123)
- Current mitigation: Using tempfile module with `delete=False` is secure
- Recommendations: Continue using `tempfile.NamedTemporaryFile()` as currently done (lines 123-125)

## Performance Bottlenecks

**Model Intensity Calculation on Every Chat Message:**
- Problem: `send_chat_message()` recalculates fit intensity from scratch each call (lines 73-85 in `ai_chat.py`)
- Files: `src/sans_webapp/services/ai_chat.py` (lines 73-85)
- Cause: DirectModel instantiation and parameter evaluation for every chat interaction, not cached
- Improvement path: Cache last computed fit curve. Invalidate only when parameters change.

**Full DataFrame Conversion for Export:**
- Problem: Building and converting entire DataFrame just to export CSV, even for large datasets
- Files: `src/sans_webapp/components/fit_results.py` (lines 250-286)
- Cause: Not streaming or incremental export
- Improvement path: For datasets >10K points, write CSV directly without DataFrame. Already acceptable for typical SANS data.

**Polydispersity Table Rendering on Every Parameter Change:**
- Problem: Full polydispersity table re-renders whenever any parameter widget changes (Streamlit rerun behavior)
- Files: `src/sans_webapp/components/parameters.py` (lines 225-328)
- Cause: Session state updates trigger full app rerun
- Improvement path: Not much to optimize here due to Streamlit architecture. Consider memoization or callbacks if performance degrades.

## Fragile Areas

**AI Model Suggestion Parser:**
- Files: `src/sans_webapp/services/ai_chat.py` (lines 172-180)
- Why fragile: Regex-based parsing of LLM response that strips numbering/bullets. If LLM format changes slightly (e.g., "1. model_name" vs "1) model_name"), parsing breaks.
- Safe modification: Add fallback heuristic if parsing yields no results. Test with various LLM response formats.
- Test coverage: `test_ai_chat_service()` tests happy path only

**Session State Key Naming Convention:**
- Files: `src/sans_webapp/components/parameters.py`, `src/sans_webapp/services/session_state.py`
- Why fragile: Session keys built with string concatenation (e.g., `f'value_{param_name}'`). No centralized definition. If convention changes, code breaks silently.
- Safe modification: Create constants or enum for key patterns. Document naming conventions. Add validation that keys exist before use.
- Test coverage: Sessions created but keys not validated

**Example Data File Path Resolution:**
- Files: `src/sans_webapp/components/sidebar.py` (lines 62-84)
- Why fragile: Multiple fallback paths to find example data (package resources, cwd, parent dirs). If bundling changes, example loading breaks silently.
- Safe modification: Single source of truth for data path. Test bundled vs installed vs development scenarios. Fail explicitly if not found.
- Test coverage: Path resolution tested manually only

**Temporary File Deletion Without Verification:**
- Files: `src/sans_webapp/components/sidebar.py` (line 135)
- Why fragile: `os.unlink()` called after file usage, but no verification of success. If file locked by another process, deletion silently fails.
- Safe modification: Check file exists after creation. Use context manager. Log deletion failures.
- Test coverage: No error case testing

## Scaling Limits

**In-Memory Data Storage:**
- Current capacity: Entire SANS dataset loaded into memory via numpy arrays
- Limit: SANS datasets typically <10K points (reasonable), but no checks for size limits
- Scaling path: For future larger datasets (>1M points), implement chunked processing or streaming

**Session State Accumulation:**
- Current capacity: Chat history and all parameter states stored in session
- Limit: Browser memory and Streamlit server memory could fill with long chat sessions or many parameter changes
- Scaling path: Implement chat history pruning. Archive old sessions. Consider persistent storage.

**Model List in Memory:**
- Current capacity: `get_all_models()` loads all sasmodels models into memory
- Limit: Acceptable (hundreds of models), but re-loaded on every page reload
- Scaling path: Cache model list. Lazy-load model details only when needed.

## Dependencies at Risk

**Streamlit Version Lock:**
- Risk: Code depends on internal Streamlit DOM selectors (`stHorizontalBlock`). Breaks on major version updates.
- Impact: Resizable columns stop working. Requires code maintenance with each Streamlit release.
- Migration plan: Remove custom JavaScript/CSS resizable columns. Use native Streamlit layout or community components.

**OpenAI SDK Version Compatibility:**
- Risk: `openai>=1.0.0` constraint is permissive. Breaking API changes in minor versions possible.
- Impact: `create_chat_completion()` signatures could change
- Migration plan: Pin to stable minor version (e.g., `openai>=1.3.0,<2.0.0`). Monitor releases.

**SASModels Version Dependency:**
- Risk: `sasmodels>=1.0` loose constraint. New models or changes to `DirectModel` API could break code
- Impact: Fit calculations, model suggestions could fail
- Migration plan: Pin to tested version range. Document minimum/maximum compatible versions.

## Missing Critical Features

**No Persistent Model Storage:**
- Problem: Fitted models and parameters lost when session ends. No save/load of models.
- Blocks: Reproducibility, batch processing, sharing results
- Solution: Add SQLite backend or CSV export of fitted models with metadata

**No Batch Processing:**
- Problem: Can only fit one dataset at a time. Manual iteration required for multiple samples.
- Blocks: High-throughput workflows common in research
- Solution: Add batch mode that processes multiple files with same model/parameters

**No Uncertainty Propagation:**
- Problem: Fit uncertainties calculated but not propagated to derived quantities
- Blocks: Scientific accuracy. Users can't compute error bars on computed properties.
- Solution: Implement error propagation using covariance matrix from fit

**Limited Visualization Options:**
- Problem: Only log-log plot available. No semi-log, linear, or custom plots
- Blocks: Diagnostic analysis. Different data types need different scales.
- Solution: Add plot style selector (log-log, log-linear, linear, linear-log, Kratky plot)

## Test Coverage Gaps

**UI Component Rendering:**
- What's not tested: Actual Streamlit rendering of UI components. Layout validation.
- Files: `src/sans_webapp/components/*.py` - all component render functions
- Risk: UI breaks silently. Column layouts, expanders, tabs could render incorrectly
- Priority: Medium (caught by manual testing, but should be automated)

**Error Handling Paths:**
- What's not tested: Exception handlers in `ai_chat.py`, `sidebar.py`, `fit_results.py`
- Files: All components with bare `except Exception` blocks
- Risk: Error messages unhelpful. Errors swallowed. Bugs in error code hidden.
- Priority: High (hidden failure modes)

**Data Validation:**
- What's not tested: CSV format validation, numeric range checks, array shape validation
- Files: `src/sans_webapp/components/sidebar.py` - data loading functions
- Risk: Invalid data produces cryptic errors or corrupts state
- Priority: Medium (important for user experience)

**Polydispersity with Different Models:**
- What's not tested: PD behavior when switching models with different PD parameters
- Files: `src/sans_webapp/components/parameters.py` (lines 364-370)
- Risk: Stale state when model changes. Tests exist in `test_polydispersity.py` but incomplete
- Priority: Medium (functional but edge cases untested)

**Integration with External Libraries:**
- What's not tested: Real calls to OpenAI API (mocked in tests), real fits with bumps/lmfit engines
- Files: `src/sans_webapp/services/ai_chat.py` - `create_chat_completion()`, fitting code
- Risk: Integration bugs discovered only in production
- Priority: High (recommend integration test suite with optional CI step)

**Session State Cleanup:**
- What's not tested: Proper deletion of temporary files, session state cleanup between tests
- Files: `src/sans_webapp/components/sidebar.py` (line 135)
- Risk: Resource leaks in long-running sessions. Tests leave orphaned files.
- Priority: Medium (good practice but not critical)

---

*Concerns audit: 2026-02-04*
