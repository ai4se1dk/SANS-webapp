---
phase: quick-001
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sans_webapp/components/parameters.py
  - src/sans_webapp/components/sidebar.py
  - tests/test_polydispersity.py
autonomous: true

must_haves:
  truths:
    - "Polydispersity UI state stays consistent when switching between models"
    - "Temporary files are cleaned up even when exceptions occur during upload"
    - "Bug fixes are validated by automated tests"
  artifacts:
    - path: "src/sans_webapp/components/parameters.py"
      provides: "Fixed PD session state validation"
      contains: "pd_enabled_key"
    - path: "src/sans_webapp/components/sidebar.py"
      provides: "Guaranteed temp file cleanup"
      contains: "try.*finally"
    - path: "tests/test_polydispersity.py"
      provides: "Test for model switching PD state"
      contains: "test_model_switch_pd_session_state"
  key_links:
    - from: "src/sans_webapp/components/parameters.py"
      to: "st.session_state"
      via: "PD state validation on model change"
      pattern: "pd_enabled.*session_state"
    - from: "src/sans_webapp/components/sidebar.py"
      to: "os.unlink"
      via: "try/finally cleanup"
      pattern: "finally.*unlink"
---

<objective>
Fix two known bugs documented in CONCERNS.md:
1. Polydispersity UI state inconsistency when switching models
2. Temporary file cleanup failure when exceptions occur during data upload

Purpose: Improve application reliability and eliminate known edge-case failures that could confuse users or leak system resources.

Output: Corrected session state management and guaranteed resource cleanup with test coverage.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/codebase/CONCERNS.md
@.planning/codebase/ARCHITECTURE.md

# Bug-specific context
@src/sans_webapp/components/parameters.py
@src/sans_webapp/components/sidebar.py
@tests/test_polydispersity.py
</context>

<tasks>

<task type="auto">
  <name>Fix polydispersity UI state inconsistency</name>
  <files>src/sans_webapp/components/parameters.py</files>
  <action>
Fix the polydispersity session state validation in `render_polydispersity_tab()` function (lines 364-370).

**Current problem:** Session state validation checks if stored pd_updates keys match current model's PD parameters, but doesn't validate other session state keys (`pd_enabled`, `pd_width_*`, `pd_n_*`, `pd_type_*`, `pd_vary_*`). When switching models, these stale keys can cause form values to not update properly.

**Fix approach:**
1. Expand the validation block (currently lines 366-370) to also check and clear `pd_enabled` session state key when model changes
2. The existing validation pattern (checking if `stored_params != current_pd_params`) correctly identifies model switches
3. Add deletion of `pd_enabled` key in the same block where `pd_updates` is deleted
4. This ensures the master enable toggle resets when switching to a model with different PD parameters

**Specific changes:**
- In the if block at line 369-370, add: `if 'pd_enabled' in st.session_state: del st.session_state['pd_enabled']`
- Keep the existing `pd_updates` deletion
- This allows the subsequent initialization at lines 374-375 to properly reset the PD state

**Why this works:** The master `pd_enabled` toggle is initialized from `fitter.is_polydispersity_enabled()` at lines 374-375. When switching models, the fitter's PD state is already reset (as confirmed in test_polydispersity.py line 352). By clearing the session state key, we force re-initialization from the fitter's clean state.
  </action>
  <verify>
Run existing tests to ensure no regression:
```bash
cd C:\Users\piotr\projects\ai\SANS-webapp
python -m pytest tests/test_polydispersity.py::TestPolydispersityMultipleModels::test_model_switch_resets_pd -v
```
  </verify>
  <done>
- Session state `pd_enabled` key is cleared when model's PD parameters change
- Existing model switch test passes
- Code follows same pattern as existing `pd_updates` cleanup
  </done>
</task>

<task type="auto">
  <name>Fix temporary file cleanup on error</name>
  <files>src/sans_webapp/components/sidebar.py</files>
  <action>
Fix temporary file cleanup in `render_data_upload_sidebar()` function (lines 123-135) to guarantee cleanup even when exceptions occur.

**Current problem:** Temporary file created at line 123-125 is only deleted at line 135, which is in the success path. If `fitter.load_data()` at line 127 raises an exception, the exception is caught at line 138 but `os.unlink()` never executes, leaving orphaned temp files.

**Fix approach:** Use try/finally pattern to ensure cleanup runs regardless of success or failure.

**Specific changes:**
1. Move the `os.unlink(tmp_file_path)` call (currently line 135) into a finally block
2. Restructure the try/except/finally as follows:
   - Keep the existing try block starting at line 118
   - Keep the existing exception handler at lines 138-141
   - Add a finally block after the except block
   - Move `os.unlink(tmp_file_path)` into the finally block
   - Add existence check before deletion: `if os.path.exists(tmp_file_path): os.unlink(tmp_file_path)`

**Why existence check:** The temp file might not exist if the error occurs during tempfile creation itself (though unlikely with `NamedTemporaryFile`). Defensive programming prevents secondary exceptions in cleanup.

**Do NOT:** Use context manager (`with tempfile.NamedTemporaryFile()`) because we need the file to persist after the with-block exits so `fitter.load_data()` can read it. The try/finally pattern is the correct solution here.
  </action>
  <verify>
Manual verification (automated test in next task):
```bash
cd C:\Users\piotr\projects\ai\SANS-webapp
python -c "import os; import tempfile; from sans_webapp.components.sidebar import render_data_upload_sidebar; print('Import successful - no syntax errors')"
```

Check the code structure:
```bash
cd C:\Users\piotr\projects\ai\SANS-webapp
python -c "
with open('src/sans_webapp/components/sidebar.py', 'r') as f:
    content = f.read()
    has_finally = 'finally:' in content[content.find('NamedTemporaryFile'):content.find('def render_model_selection')]
    has_unlink_in_finally = 'os.unlink' in content[content.find('finally:'):content.find('def render_model_selection')] if has_finally else False
    print(f'Has finally block: {has_finally}')
    print(f'Has unlink in finally: {has_unlink_in_finally}')
    if has_finally and has_unlink_in_finally:
        print('✓ Cleanup structure looks correct')
    else:
        print('✗ Cleanup structure needs review')
"
```
  </verify>
  <done>
- `os.unlink(tmp_file_path)` is inside a finally block
- Finally block executes after both success and exception paths
- File existence check prevents errors if file was never created
- Code maintains existing error handling behavior
  </done>
</task>

<task type="auto">
  <name>Add test for model switching PD session state</name>
  <files>tests/test_polydispersity.py</files>
  <action>
Add a test to `TestPolydispersityMultipleModels` class to verify that PD session state is properly cleared when switching models. This validates the fix from Task 1.

**Add test method:**

```python
def test_model_switch_pd_session_state_cleanup(self):
    """Test that switching models clears stale PD session state keys."""
    from unittest.mock import MagicMock, patch

    fitter = SANSFitter()

    # Start with sphere model
    fitter.set_model('sphere')
    fitter.enable_polydispersity(True)

    # Simulate session state with PD enabled
    mock_session_state = {
        'fitter': fitter,
        'pd_enabled': True,
        'pd_updates': {'radius': {'pd_width': 0.1, 'pd_n': 35, 'pd_type': 'gaussian', 'vary': True}},
    }

    with patch('sans_webapp.components.parameters.st') as mock_st:
        # Setup mock session state
        mock_st.session_state = MagicMock()
        mock_st.session_state.__contains__ = lambda self, key: key in mock_session_state
        mock_st.session_state.__getitem__ = lambda self, key: mock_session_state[key]
        mock_st.session_state.__setitem__ = lambda self, key, val: mock_session_state.__setitem__(key, val)

        deleted_keys = []

        def mock_delitem(key):
            deleted_keys.append(key)
            del mock_session_state[key]

        mock_st.session_state.__delitem__ = mock_delitem

        # Switch to cylinder model (different PD params: radius + length)
        fitter.set_model('cylinder')

        # Mock the necessary streamlit components to prevent actual rendering
        mock_st.info = MagicMock()
        mock_st.checkbox = MagicMock(return_value=False)

        # Import and call render function - this should trigger validation
        from sans_webapp.components.parameters import render_polydispersity_tab
        render_polydispersity_tab(fitter)

        # Verify that stale session state was cleared
        assert 'pd_updates' in deleted_keys, "pd_updates should be deleted when model changes"
        assert 'pd_enabled' in deleted_keys, "pd_enabled should be deleted when model changes"
```

**Placement:** Add this method to the `TestPolydispersityMultipleModels` class after the existing `test_model_switch_resets_pd` method (after line 354).

**Why this test matters:** The existing `test_model_switch_resets_pd` tests that the fitter resets PD state when switching models. This new test validates that the Streamlit UI session state is also cleared, preventing stale UI state from persisting across model changes.
  </action>
  <verify>
Run the new test:
```bash
cd C:\Users\piotr\projects\ai\SANS-webapp
python -m pytest tests/test_polydispersity.py::TestPolydispersityMultipleModels::test_model_switch_pd_session_state_cleanup -v
```

Run all polydispersity tests to ensure no regression:
```bash
cd C:\Users\piotr\projects\ai\SANS-webapp
python -m pytest tests/test_polydispersity.py -v
```
  </verify>
  <done>
- New test method `test_model_switch_pd_session_state_cleanup` exists in `TestPolydispersityMultipleModels` class
- Test validates that both `pd_updates` and `pd_enabled` session keys are deleted on model switch
- Test passes, confirming the bug fix works correctly
- All existing polydispersity tests still pass
  </done>
</task>

</tasks>

<verification>
1. **PD state consistency:**
   - Switch from sphere to cylinder model in running app
   - Verify PD checkbox state resets appropriately
   - No stale form values from previous model

2. **Temp file cleanup:**
   - Verify no orphaned temp files in system temp directory
   - Check that cleanup happens even when load_data raises exception

3. **Test coverage:**
   - All polydispersity tests pass
   - New test specifically validates session state cleanup

4. **No regressions:**
   - Run full test suite: `python -m pytest tests/ -v`
   - No new failures introduced
</verification>

<success_criteria>
- [ ] Polydispersity session state `pd_enabled` key is cleared when model's PD parameters change
- [ ] Temporary file cleanup uses try/finally pattern with existence check
- [ ] New test `test_model_switch_pd_session_state_cleanup` passes
- [ ] All existing tests continue to pass
- [ ] No syntax errors or import failures
- [ ] Code follows existing patterns in codebase (session state management, error handling)
</success_criteria>

<output>
After completion, create `.planning/quick/001-fix-known-bugs/001-SUMMARY.md`
</output>
