# Testing Patterns

**Analysis Date:** 2026-02-04

## Test Framework

**Runner:**
- pytest 7.0+ (from `pyproject.toml` dependencies)
- Config: `pyproject.toml` contains `[tool.pytest.ini_options]`

**Assertion Library:**
- Python standard `assert` statements
- No external assertion library needed (pytest provides rich comparison output)

**Run Commands:**
```bash
pixi run test                 # Run all tests (-v flag verbose)
pixi run test-verbose        # Run tests with very verbose output (-vv)
pixi run test-coverage       # Run with coverage report (html, term, xml)
pixi run test-quick          # Quick run with first failure stop (-x flag)
```

**Direct pytest invocation:**
```bash
pytest tests/ -v             # Verbose
pytest tests/ --cov=.        # Coverage
pytest tests/ -m "not slow"  # Exclude slow tests
```

## Test File Organization

**Location:**
- Tests co-located in separate `tests/` directory at project root
- Parallel to `src/` structure

**Naming:**
- Test files: `test_*.py` (pytest discovery pattern)
- Test classes: `Test*` (CamelCase for grouping related tests)
- Test functions: `test_*` (snake_case, descriptive)

**Structure:**
```
tests/
├── __init__.py              # Empty init file
├── test_app.py              # Main app tests (1616 lines)
└── test_polydispersity.py   # Polydispersity feature tests (462 lines)
```

**Pytest discovery configuration (from pyproject.toml):**
```toml
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

## Test Structure

**Suite Organization:**
```python
# From tests/test_polydispersity.py
class TestPolydispersityUIConstants:
    """Test polydispersity UI constants."""

    def test_tab_labels_exist(self):
        """Test that tab labels are defined."""
        assert PARAM_TAB_BASIC is not None
        assert PARAM_TAB_POLYDISPERSITY is not None
```

**Patterns:**
- **Setup/Initialization:** No explicit setup methods; fixtures instantiated directly in tests
  ```python
  # From tests/test_polydispersity.py
  def test_apply_pd_updates_to_fitter(self):
      """Test that PD updates are correctly applied to fitter."""
      fitter = SANSFitter()
      fitter.set_model('sphere')
      # ... test body
  ```

- **Assertions:** Simple assertions with descriptive messages
  ```python
  assert len(models) > 0, 'No models found!'
  assert 'sphere' in models, 'sphere model not found!'
  ```

- **Test isolation:** Each test creates its own instances (no shared state)

## Mocking

**Framework:** `unittest.mock` (standard library)

**Patterns:**
```python
# From tests/test_polydispersity.py (line 12, 87-115)
from unittest.mock import MagicMock, patch

def test_clear_parameter_state_clears_pd_keys(self):
    """Test that clear_parameter_state removes PD-related keys."""
    mock_session_state = {
        'fitter': MagicMock(),
        'data_loaded': True,
        'value_radius': 50.0,
        # ... other keys
    }

    deleted_keys = []

    class MockSessionState:
        def keys(self):
            return list(mock_session_state.keys())

        def __delitem__(self, key):
            deleted_keys.append(key)
            del mock_session_state[key]

    with patch('sans_webapp.services.session_state.st') as mock_st:
        mock_st.session_state = MockSessionState()
        clear_parameter_state()
        assert 'pd_enabled' in deleted_keys
```

**What to Mock:**
- Streamlit module (`st`) for tests that import components (no actual UI rendering)
- Complex external services (OpenAI API calls)
- External dependencies not core to test logic

**What NOT to Mock:**
- Core business logic (`SANSFitter`, data structures)
- Type definitions and constants
- Pure utility functions

## Fixtures and Factories

**Test Data:**
```python
# From tests/test_app.py (line 51-66)
def test_utils_analyze_data():
    """Test data analysis for AI suggestion from utils module."""
    # Create fake data
    q = np.logspace(-3, -1, 50)
    i = 100 * np.exp(-q * 10) + 0.1

    description = utils.analyze_data_for_ai_suggestion(q, i)
    assert len(description) > 0, 'No description generated!'
    assert 'Q range' in description, 'Q range not in description!'
```

**Location:**
- Fixtures inline within test functions (not in conftest.py)
- Example data created procedurally with numpy: `np.logspace()`, `np.exp()`

**Factory Pattern:** Not explicitly used; simple instantiation preferred:
```python
# From tests/test_polydispersity.py
def test_apply_pd_updates_multiple_params(self):
    fitter = SANSFitter()  # Simple factory-like creation
    fitter.set_model('cylinder')
```

## Coverage

**Requirements:**
- No minimum coverage threshold enforced by pytest configuration
- Coverage reports generated but not gated on CI

**View Coverage:**
```bash
pixi run test-coverage       # Generates html/term/xml reports
```

**Configuration (from pyproject.toml):**
```toml
[tool.coverage.run]
source = ["."]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
    "*/venv/*",
    "*/env/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Test Types

**Unit Tests:**
- **Scope:** Individual functions and classes (80% of test suite)
- **Approach:** Direct function calls with isolated instances
- **Example:** `test_utils_analyze_data()` tests data analysis without Streamlit
- **Location:** Throughout `tests/test_app.py` and `tests/test_polydispersity.py`

**Integration Tests:**
- **Scope:** Component workflows (data loading → model selection → fitting)
- **Approach:** Mocks Streamlit but uses real business logic classes
- **Example from test_polydispersity.py:**
  ```python
  class TestPolydispersityWorkflow:
      """Test complete polydispersity workflow integration."""
      # Tests full feature workflows
  ```
- **Location:** Class-based tests grouping related workflows

**E2E Tests:**
- **Framework:** Not used (no Selenium, Cypress, or similar)
- **Reason:** Streamlit apps require browser testing; manual verification used instead

## Test Markers

**Available markers (from pyproject.toml):**
```toml
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

**Usage:**
```bash
pytest tests/ -m "not slow"      # Skip slow tests
pytest tests/ -m "integration"   # Run only integration tests
```

## Common Patterns

**Async Testing:**
- Not applicable (no async code in codebase)

**Error Testing:**
```python
# From tests/test_app.py - general pattern shown
def test_utils_suggest_models_simple():
    """Test simple model suggestion from utils module."""
    # Test with steep decay (spherical particles)
    q = np.logspace(-3, -1, 50)
    i_steep = 100 * q ** (-4) + 0.1  # Porod law for spheres
    suggestions_steep = utils.suggest_models_simple(q, i_steep)
    assert len(suggestions_steep) > 0, 'No suggestions generated for steep decay!'
```

**Parametrized Testing:** Not detected in codebase; individual test functions used instead

**Test Output:**
```toml
# From pyproject.toml
addopts = [
    "-v",                          # Verbose output
    "--tb=short",                  # Shorter traceback format
    "--strict-markers",            # Strict marker usage
    "-ra",                         # Show summary of all test outcomes
    "--disable-warnings",          # Disable warnings display
]
```

## Testing Best Practices Observed

1. **Descriptive test names:** `test_apply_pd_updates_multiple_params()` clearly states what is tested
2. **Docstrings on all test functions:** Required for test discovery and documentation
3. **One assertion per test when possible:** Some tests have multiple assertions for related checks
4. **Clear mock usage:** Streamlit mocking isolated to specific test sections
5. **No global test fixtures:** Tests are self-contained and independent
6. **Organized by feature:** Test classes group related functionality

---

*Testing analysis: 2026-02-04*
