# Testing Patterns

**Analysis Date:** 2026-02-05

## Test Framework

**Runner:**
- pytest 7.0+
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Assertion Library:**
- Built-in pytest assertions with assert statements

**Run Commands:**
```bash
pixi run test              # Run all tests with verbose output
pixi run test-verbose      # Run all tests with very verbose output
pixi run test-coverage     # Run with coverage (HTML, terminal, XML reports)
pixi run test-quick        # Run with early exit on first failure (-x flag)
```

**Test Discovery:**
- Test paths: `tests/`
- Test file pattern: `test_*.py`
- Test class pattern: `Test*`
- Test function pattern: `test_*`

## Test File Organization

**Location:**
- Co-located in `tests/` directory parallel to source
- Pattern: `tests/test_<module_name>.py` mirrors `src/sans_webapp/<module_name>.py`

**Naming:**
- Test files: `test_ai_chat.py`, `test_app_init.py`, `test_sans_types.py`, `test_mcp_tools.py`
- Test classes: `TestBuildContext`, `TestSuggestModelsAI`, `TestSendChatMessage`
- Test functions: `test_build_context_includes_model`, `test_send_chat_message_returns_string`

**Structure:**
```
tests/
├── conftest.py                 # Shared fixtures and mock classes
├── test_ai_chat.py            # Tests for ai_chat service
├── test_app_init.py           # Tests for app initialization
├── test_env_config.py         # Environment configuration tests
├── test_mcp_tools.py          # Tests for MCP server tools
├── test_polydispersity.py     # Tests for polydispersity features
├── test_sans_types.py         # Tests for type definitions
├── test_sidebar_ai_chat.py    # Tests for AI chat UI component
└── __init__.py                # Empty init file
```

## Test Structure

**Suite Organization:**
```python
class TestBuildContext:
    """Test the context building for AI chat."""

    def test_build_context_includes_model(self, mock_fitter):
        """Context should include model information."""
        from sans_webapp.services.ai_chat import _build_context

        context = _build_context(mock_fitter)

        assert 'sphere' in context.lower() or 'model' in context.lower()
```

**Patterns:**
- Class-based test organization by function or component
- Docstrings describe test purpose (what it tests)
- Setup via pytest fixtures (avoid setUp/tearDown methods)
- Clear assertion messages; use simple `assert` statements

## Mocking

**Framework:** `unittest.mock` (Python standard library)

**Patterns:**
Mock classes defined in `conftest.py` for reuse:
```python
class MockSessionState:
    """Mock for Streamlit session_state."""

    def __init__(self):
        self._data = {
            'ai_tools_enabled': True,
            'needs_rerun': False,
            'current_model': None,
            # ... more keys
        }

    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data
```

Mock class pattern for SANSFitter:
```python
class MockFitter:
    """Mock for SANSFitter."""

    def __init__(self):
        self.model = None
        self.data = None
        self.params = {}
        self.result = None

    def set_model(self, model_name: str):
        self.model = MagicMock()
        self.model.name = model_name
        self.params = {
            'radius': MagicMock(value=50.0, bounds=(1, 500), vary=True),
            # ... more params
        }
        return self
```

**Usage in Tests:**
```python
with patch('sans_webapp.services.ai_chat.get_claude_client') as mock_get_client:
    with patch('sans_webapp.services.ai_chat.st') as mock_st:
        mock_st.session_state = MockSessionState()

        mock_client = MagicMock()
        mock_client.simple_chat.return_value = "Response text"
        mock_get_client.return_value = mock_client

        result = send_chat_message("Hello", "api-key", mock_fitter)

        assert isinstance(result, str)
```

**What to Mock:**
- External API clients: `get_claude_client()`, `create_chat_completion()`
- Streamlit module: `st`, `st.session_state`
- File system operations: `files()`, `Path.exists()`
- MCP server operations: `set_fitter()`, `set_state_accessor()`

**What NOT to Mock:**
- Business logic being tested
- TypedDict definitions
- Pure utility functions
- Data structures (numpy arrays, lists, dicts)

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def mock_fitter_with_model():
    """Create a mock fitter with a model already loaded."""
    fitter = MockFitter()
    fitter.set_model('sphere')
    return fitter

@pytest.fixture
def mock_fitter_full():
    """Create a mock fitter with both model and data."""
    fitter = MockFitter()
    fitter.load_data('test_data.csv')
    fitter.set_model('sphere')
    return fitter
```

**Location:**
- Shared fixtures in `tests/conftest.py`: `mock_session_state`, `mock_fitter`, `mock_fitter_with_model`, `mock_fitter_with_data`, `mock_fitter_full`
- Test-specific fixtures defined in test files when needed
- Mock classes as part of fixture setup

## Coverage

**Requirements:** No enforced minimum coverage target

**View Coverage:**
```bash
pixi run test-coverage
# Generates: htmlcov/index.html, coverage.xml, terminal output
```

**Configuration:**
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
- Scope: Individual functions and methods in isolation
- Approach: Mock all external dependencies (Streamlit, API clients, file system)
- Examples: `test_build_context_includes_model`, `test_send_chat_message_returns_string`
- Location: `tests/test_*.py` files
- Pattern: Test private and public functions

**Integration Tests:**
- Scope: Multiple components working together
- Approach: Mock only external services (APIs, file I/O)
- Marked with `@pytest.mark.integration` (optional)
- Examples: Testing chat flow with mocked Claude client but real session state logic

**E2E Tests:**
- Framework: Not used in current codebase
- Note: Streamlit apps are better tested with Streamlit's `streamlit run --logger.level=debug` and manual testing

**Markers:**
```toml
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

## Common Patterns

**Async Testing:**
Not applicable; codebase uses synchronous execution with Streamlit's event loop.

**Error Testing:**
```python
def test_send_chat_message_handles_error(self, mock_fitter):
    """send_chat_message should handle errors gracefully."""
    from sans_webapp.services.ai_chat import send_chat_message

    with patch('sans_webapp.services.ai_chat.get_claude_client') as mock_get_client:
        with patch('sans_webapp.services.ai_chat.st') as mock_st:
            mock_st.session_state = MockSessionState()
            mock_get_client.side_effect = Exception("API error")

            result = send_chat_message("Hello", "api-key", mock_fitter)

            assert isinstance(result, str)
            assert 'error' in result.lower()
```

**TypedDict Testing:**
```python
def test_mcp_tool_result_fields():
    sample: MCPToolResult = {
        'tool_name': 'set-model',
        'input': {'model_name': 'sphere'},
        'result': "Model 'sphere' loaded",
        'success': True,
    }

    assert sample['tool_name'] == 'set-model'
    assert isinstance(sample['input'], dict)
    assert sample['success'] is True
```

**Parametrized Testing:**
Not heavily used; individual test cases are preferred for clarity.

**Mock Return Value Testing:**
```python
def test_returns_response_and_tools_invoked(self, mock_fitter):
    with patch('sans_webapp.services.ai_chat.get_claude_client') as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.return_value = ("Response text", [{"tool_name": "set-model"}])
        mock_get_client.return_value = mock_client

        response, tools_invoked, needs_rerun = send_chat_message_with_tools(
            "Use sphere model",
            "api-key",
            mock_fitter
        )

        assert isinstance(response, str)
        assert isinstance(tools_invoked, list)
```

## Test Execution

**Pytest Configuration Options:**
```toml
addopts = [
    "-v",                          # Verbose output
    "--tb=short",                  # Shorter traceback format
    "--strict-markers",            # Strict marker usage
    "-ra",                         # Show summary of all test outcomes
    "--disable-warnings",          # Disable warnings display
]
```

**Running Specific Tests:**
```bash
pytest tests/test_ai_chat.py::TestSendChatMessage::test_send_chat_message_returns_string -v
pytest tests/test_app_init.py -v
pytest -m "not slow" --cov=src/sans_webapp tests/
```

---

*Testing analysis: 2026-02-05*
