# Plan: Integrate SANS-pilot Chat into SANS-webapp

## Overview

Replace the current simple OpenAI chat implementation in `render_ai_chat_sidebar` with SANS-pilot's full agentic LLM functionality, allowing the AI chat to execute SANS-fitter commands and update the webapp's plots.

## Current State Analysis

### SANS-webapp (Current Implementation)
- **Location**: `src/sans_webapp/components/sidebar.py` - `render_ai_chat_sidebar()`
- **Location**: `src/sans_webapp/services/ai_chat.py` - `send_chat_message()`, `suggest_models_ai()`
- Uses direct OpenAI API calls with limited prompt
- Chat history stored in `st.session_state.chat_history`
- Has access to `SANSFitter` instance but limited capability to execute commands
- UI components: text area input, send/clear buttons, chat history display

### SANS-pilot (Target Implementation)
- **Package**: `sans_pilot`
- **Key Modules**:
  - `chat_agent.py` - Main agent implementation with LangChain
  - `tools.py` - Tool definitions for SANS-fitter operations (set_radius, fit, load_model, etc.)
  - `prompts.py` - System prompts and agent instructions
  - `cli.py` - CLI interface (reference for standalone usage)
  - `utils.py` - Utility functions
- Uses LangChain AgentExecutor with tool calling
- Can execute SANS-fitter operations via LLM tool calls

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SANS-webapp                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Streamlit UI                             │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │ │
│  │  │ Data Upload │  │Model Select  │  │   AI Chat Pane   │  │ │
│  │  └─────────────┘  └──────────────┘  └────────┬─────────┘  │ │
│  │                                              │             │ │
│  │  ┌───────────────────────────────────────────▼───────────┐ │ │
│  │  │                   Main Area                            │ │ │
│  │  │  ┌─────────────────┐  ┌─────────────────────────────┐ │ │ │
│  │  │  │  Plot Display   │  │   Parameter Controls        │ │ │ │
│  │  │  │  (plotly/mpl)   │  │   (sliders, inputs)         │ │ │ │
│  │  │  └────────▲────────┘  └──────────────▲──────────────┘ │ │ │
│  │  └───────────┼────────────────────────────┼──────────────┘ │ │
│  └──────────────┼────────────────────────────┼────────────────┘ │
│                 │                            │                   │
│  ┌──────────────┴────────────────────────────┴────────────────┐ │
│  │              st.session_state                               │ │
│  │  • fitter: SANSFitter                                       │ │
│  │  • model_selected: bool                                     │ │
│  │  • data_loaded: bool                                        │ │
│  │  • fit_completed: bool                                      │ │
│  │  • chat_history: list                                       │ │
│  │  • pilot_agent: PilotAgent  ◄─── NEW                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                 │                                                │
│  ┌──────────────▼────────────────────────────────────────────┐  │
│  │              SANS-pilot (imported package)                  │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │  PilotAgent / SANSAgent                              │   │  │
│  │  │  • Wraps SANSFitter with tools                       │   │  │
│  │  │  • LangChain AgentExecutor                           │   │  │
│  │  │  • Callback hooks for UI updates                     │   │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: SANS-pilot Package Modifications

#### 1.1 Create Callback/Hook System for External UI Updates

**File**: `sans_pilot/callbacks.py` (NEW)

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class PilotUICallback(ABC):
    """Abstract callback interface for UI updates from SANS-pilot."""
    
    @abstractmethod
    def on_parameter_changed(self, param_name: str, value: float) -> None:
        """Called when a model parameter is changed."""
        pass
    
    @abstractmethod
    def on_model_changed(self, model_name: str) -> None:
        """Called when the model is changed."""
        pass
    
    @abstractmethod
    def on_fit_completed(self, result: Dict[str, Any]) -> None:
        """Called when a fit operation completes."""
        pass
    
    @abstractmethod
    def on_data_loaded(self, data_info: Dict[str, Any]) -> None:
        """Called when data is loaded."""
        pass
    
    @abstractmethod
    def request_plot_update(self) -> None:
        """Called to request UI plot refresh."""
        pass
```

#### 1.2 Modify Agent to Accept External SANSFitter and Callbacks

**File**: `sans_pilot/chat_agent.py` (MODIFY)

- Add constructor parameter for external `SANSFitter` instance
- Add constructor parameter for `PilotUICallback`
- Modify tools to invoke callbacks after operations
- Ensure tools don't create internal plots (delegate to callback)

```python
class SANSPilotAgent:
    def __init__(
        self,
        api_key: str,
        fitter: Optional[SANSFitter] = None,  # Accept external fitter
        ui_callback: Optional[PilotUICallback] = None,  # UI callback
        model: str = "gpt-4o",
    ):
        self.fitter = fitter or SANSFitter()
        self.ui_callback = ui_callback
        # ... agent setup
```

#### 1.3 Modify Tools to Support External UI

**File**: `sans_pilot/tools.py` (MODIFY)

- Modify each tool to accept optional callback
- After tool execution, invoke appropriate callback method
- Return structured result that UI can interpret

Example modification:
```python
@tool
def set_parameter(param_name: str, value: float) -> str:
    """Set a model parameter value."""
    result = agent.fitter.set_param(param_name, value)
    if agent.ui_callback:
        agent.ui_callback.on_parameter_changed(param_name, value)
        agent.ui_callback.request_plot_update()
    return f"Set {param_name} to {value}"
```

#### 1.4 Export Public API

**File**: `sans_pilot/__init__.py` (MODIFY)

```python
from .chat_agent import SANSPilotAgent
from .callbacks import PilotUICallback
from .tools import get_available_tools

__all__ = [
    'SANSPilotAgent',
    'PilotUICallback',
    'get_available_tools',
]
```

---

### Phase 2: SANS-webapp Integration

#### 2.1 Add SANS-pilot Dependency

**File**: `pyproject.toml` (MODIFY)

```toml
[project]
dependencies = [
    # ... existing deps
    "sans-pilot",  # or path dependency during development
]
```

For development:
```toml
[tool.setuptools.package-data]
# or use pip install -e ../SANS-pilot
```

#### 2.2 Create Streamlit-specific Callback Implementation

**File**: `src/sans_webapp/services/pilot_integration.py` (NEW)

```python
from typing import Any, Dict
import streamlit as st
from sans_pilot import PilotUICallback

class StreamlitPilotCallback(PilotUICallback):
    """Streamlit-specific implementation of PilotUICallback."""
    
    def on_parameter_changed(self, param_name: str, value: float) -> None:
        """Update session state when parameter changes."""
        # Update the session state widget values
        st.session_state[f'value_{param_name}'] = value
    
    def on_model_changed(self, model_name: str) -> None:
        """Handle model change."""
        st.session_state.current_model = model_name
        st.session_state.model_selected = True
        # Clear old parameter widgets
        keys_to_remove = [k for k in st.session_state.keys() 
                         if k.startswith(('value_', 'min_', 'max_', 'vary_'))]
        for key in keys_to_remove:
            del st.session_state[key]
    
    def on_fit_completed(self, result: Dict[str, Any]) -> None:
        """Handle fit completion."""
        st.session_state.fit_completed = True
        st.session_state.fit_result = result
    
    def on_data_loaded(self, data_info: Dict[str, Any]) -> None:
        """Handle data load."""
        st.session_state.data_loaded = True
    
    def request_plot_update(self) -> None:
        """Trigger Streamlit rerun to update plots."""
        # Set a flag that the main area can check
        st.session_state.plot_needs_update = True
```

#### 2.3 Create Agent Manager

**File**: `src/sans_webapp/services/pilot_integration.py` (CONTINUE)

```python
from sans_pilot import SANSPilotAgent
from typing import Optional

def get_or_create_pilot_agent(
    api_key: str,
    fitter: "SANSFitter"
) -> SANSPilotAgent:
    """Get or create the SANS-pilot agent instance."""
    
    # Check if we need to create/recreate the agent
    if 'pilot_agent' not in st.session_state or \
       st.session_state.get('pilot_api_key') != api_key:
        
        callback = StreamlitPilotCallback()
        st.session_state.pilot_agent = SANSPilotAgent(
            api_key=api_key,
            fitter=fitter,
            ui_callback=callback,
        )
        st.session_state.pilot_api_key = api_key
    
    return st.session_state.pilot_agent


def send_pilot_message(
    message: str,
    api_key: str,
    fitter: "SANSFitter"
) -> str:
    """Send a message to the SANS-pilot agent and get response."""
    agent = get_or_create_pilot_agent(api_key, fitter)
    
    # Get chat history from session state
    history = st.session_state.get('chat_history', [])
    
    # Invoke agent with message and history
    response = agent.chat(message, history=history)
    
    return response
```

#### 2.4 Modify render_ai_chat_sidebar

**File**: `src/sans_webapp/components/sidebar.py` (MODIFY)

Replace the current implementation:

```python
from sans_webapp.services.pilot_integration import send_pilot_message

def render_ai_chat_sidebar(api_key: Optional[str], fitter: SANSFitter) -> None:
    """
    Render the AI Chat pane using SANS-pilot agent.
    
    Args:
        api_key: OpenAI API key
        fitter: The SANSFitter instance (shared with main app)
    """
    with st.sidebar:
        st.markdown('---')
        with st.expander(AI_CHAT_SIDEBAR_HEADER, expanded=st.session_state.show_ai_chat):
            st.markdown(AI_CHAT_DESCRIPTION)

            # Initialize chat history
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []

            # Chat input
            user_prompt = st.text_area(
                'Your message:',
                height=CHAT_INPUT_HEIGHT,
                placeholder=AI_CHAT_INPUT_PLACEHOLDER,
                key='chat_input',
                label_visibility='collapsed',
            )

            # Buttons
            col_send, col_clear = st.columns([1, 1])
            with col_send:
                send_clicked = st.button(AI_CHAT_SEND_BUTTON, type='primary')
            with col_clear:
                clear_clicked = st.button(AI_CHAT_CLEAR_BUTTON)

            if clear_clicked:
                st.session_state.chat_history = []
                if 'pilot_agent' in st.session_state:
                    del st.session_state.pilot_agent
                st.rerun()

            if send_clicked and user_prompt.strip():
                if not api_key:
                    st.warning("Please provide an API key")
                else:
                    with st.spinner(AI_CHAT_THINKING):
                        # Use SANS-pilot for the response
                        response = send_pilot_message(
                            user_prompt.strip(),
                            api_key,
                            fitter
                        )
                        
                        # Update chat history
                        st.session_state.chat_history.append(
                            {'role': 'user', 'content': user_prompt.strip()}
                        )
                        st.session_state.chat_history.append(
                            {'role': 'assistant', 'content': response}
                        )
                    
                    # Rerun to update UI (plots may have changed)
                    st.rerun()

            # Display chat history
            st.markdown('---')
            st.markdown(AI_CHAT_HISTORY_HEADER)
            
            # ... rest of chat history display (unchanged)
```

#### 2.5 Update Main App to Handle Plot Updates

**File**: `src/sans_webapp/app.py` (MODIFY)

Add check for plot update requests:

```python
def main():
    # ... existing initialization
    
    # Check if pilot requested plot update
    if st.session_state.get('plot_needs_update', False):
        st.session_state.plot_needs_update = False
        # The plot will automatically use updated fitter state
    
    # ... rest of main app
```

---

### Phase 3: Data Flow Implementation

#### 3.1 Shared State Architecture

```
User Input (Chat) ──► SANS-pilot Agent
                           │
                           ├── Tool: set_parameter()
                           │      │
                           │      └── Updates fitter ──► Callback ──► st.session_state
                           │
                           ├── Tool: fit()
                           │      │
                           │      └── Runs fit ──► Callback ──► st.session_state
                           │
                           └── Tool: set_model()
                                  │
                                  └── Changes model ──► Callback ──► st.session_state
                                  
st.session_state.fitter ◄────────────────────────────────────────┘
         │
         ▼
    Plot Rendering (main area) reads from fitter.data, fitter.result
```

#### 3.2 Key Session State Variables

| Variable | Type | Purpose |
|----------|------|---------|
| `fitter` | SANSFitter | Shared fitting instance |
| `pilot_agent` | SANSPilotAgent | SANS-pilot agent instance |
| `chat_history` | List[Dict] | Chat conversation history |
| `plot_needs_update` | bool | Flag for plot refresh |
| `model_selected` | bool | Model selection state |
| `data_loaded` | bool | Data load state |
| `fit_completed` | bool | Fit completion state |

---

### Phase 4: Testing & Validation

#### 4.1 Unit Tests

- Test `StreamlitPilotCallback` with mock session state
- Test `send_pilot_message` with mock agent
- Test agent creation and reuse

#### 4.2 Integration Tests

- Test parameter change via chat updates plot
- Test model change via chat triggers correct state updates
- Test fit via chat shows results
- Test data load via chat enables model selection

#### 4.3 User Acceptance Tests

| Test Case | Input | Expected Result |
|-----------|-------|-----------------|
| Set radius | "Set radius to 50" | radius=50 in fitter, plot updates |
| Change model | "Use cylinder model" | Model changes, parameters reset |
| Run fit | "Fit the data" | Fit runs, results displayed |
| Multi-action | "Set radius=30, scale=0.5 and fit" | All actions execute, plot updates |

---

## Migration Checklist

- [ ] **Phase 1: SANS-pilot modifications**
  - [ ] Add `callbacks.py` with `PilotUICallback` ABC
  - [ ] Modify `chat_agent.py` to accept external fitter and callback
  - [ ] Modify `tools.py` to invoke callbacks
  - [ ] Update `__init__.py` exports
  - [ ] Add tests for callback integration
  - [ ] Bump version and publish/update

- [ ] **Phase 2: SANS-webapp integration**
  - [ ] Add sans-pilot dependency to pyproject.toml
  - [ ] Create `pilot_integration.py` with `StreamlitPilotCallback`
  - [ ] Create agent manager functions
  - [ ] Modify `render_ai_chat_sidebar` to use SANS-pilot
  - [ ] Update main app for plot refresh handling
  - [ ] Remove old `ai_chat.py` (or deprecate)
  - [ ] Update imports in sidebar.py

- [ ] **Phase 3: Testing**
  - [ ] Unit tests for new components
  - [ ] Integration tests for chat-to-plot flow
  - [ ] Manual UAT for all chat commands

- [ ] **Phase 4: Documentation**
  - [ ] Update README with new chat capabilities
  - [ ] Document supported chat commands
  - [ ] Add developer docs for extending tools

---

## Refinements to Add Before Implementation

### Compatibility & Packaging
- Define a minimum SANS-pilot version and pin it in SANS-webapp.
- Add a simple compatibility matrix (SANS-webapp ↔ SANS-pilot ↔ SANS-fitter versions).
- Decide packaging approach: PyPI release vs local editable path for development.

### Tool Side-Effects & Ordering
- Define deterministic tool behavior (idempotent where possible).
- Enforce sequential tool execution per chat message to avoid inconsistent state.
- Record tool execution results in a structured log to aid debugging.

### Error Handling & Rollback
- Standardize tool error responses (user-facing message + internal diagnostics).
- Decide rollback behavior on partial failures (e.g., revert parameter changes if fit fails).
- Surface tool failures as assistant messages with clear next steps.

### Plot Refresh Semantics
- Explicitly document how plots read from `st.session_state.fitter`.
- Define when to set `plot_needs_update` and when to clear it (before/after rerun).
- Prevent rapid reruns by debouncing multiple tool updates within one agent response.

### Chat History Format Alignment
- Document the expected SANS-pilot history schema and add conversion in webapp.
- Add a migration step if the current webapp history format differs.

### Agent Reset Behavior
- Add a "reset agent" action when data or model changes (prevents stale context).
- Keep the UI reset aligned with `st.session_state.chat_history` resets.

### Stable Tool API Contract
- Document tool names and argument schemas as a stable API surface.
- Add a quick reference table of tools in the plan for future extension.

### No-UI Side-Effects Mode
- Add a "headless" mode for CLI/testing where callbacks are no-ops.
- Ensure tools still return structured results in headless mode.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes in SANS-pilot API | High | Pin version, add integration tests |
| Streamlit rerun conflicts | Medium | Careful state management, debouncing |
| Agent response latency | Medium | Add loading indicators, async where possible |
| Token usage costs | Medium | Implement conversation summarization for long chats |

---

## Future Enhancements

1. **Multiple LLM providers**: Use SANS-pilot's LLM abstraction to support Claude, Gemini, etc.
2. **Conversation memory**: Persist chat history across sessions
3. **Tool suggestions**: Show available commands to users
4. **Streaming responses**: Display agent responses as they stream
5. **Error recovery**: Better handling of failed tool calls
