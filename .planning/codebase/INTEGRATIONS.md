# External Integrations

**Analysis Date:** 2026-02-04

## APIs & External Services

**AI/Chat:**
- OpenAI API - AI-powered model suggestions and interactive chat assistance
  - SDK/Client: `openai>=1.0.0`
  - Implementation file: `src/sans_webapp/openai_client.py`
  - Model used: `gpt-4o` (hardcoded in `src/sans_webapp/services/ai_chat.py` line 107)
  - Auth: API key provided by user via Streamlit UI (`src/sans_webapp/components/sidebar.py` line 166-170)
  - Max tokens: 1000 per request
  - Endpoints:
    - Chat completions: `POST https://api.openai.com/v1/chat/completions`
  - Integration points:
    - `src/sans_webapp/openai_client.py:create_chat_completion()` - Core API wrapper
    - `src/sans_webapp/services/ai_chat.py:send_chat_message()` - Chat message handling
    - `src/sans_webapp/services/ai_chat.py:suggest_models_ai()` - Model suggestion with AI

## Data Storage

**Databases:**
- None - Application is stateless
- Data loading: CSV and .dat file formats only
  - No persistent database layer
  - Session state stored in Streamlit's memory (not persisted)

**File Storage:**
- Local filesystem only
  - Temporary files: `tempfile.NamedTemporaryFile()` for uploads (see `src/sans_webapp/components/sidebar.py` line 123-125)
  - Example data: Bundled in package at `src/sans_webapp/data/` (configured in `pyproject.toml`)
  - Simulation data: `simulated_sans_data.csv` in project root

**Caching:**
- Streamlit session state (`st.session_state`) - In-memory caching during user session
  - Chat history: `st.session_state.chat_history`
  - AI suggestions: `st.session_state.ai_suggestions`
  - Fitter state: `st.session_state.fitter`
  - No external caching service

## Authentication & Identity

**Auth Provider:**
- Custom/Manual - OpenAI API key input via UI
  - Implementation: `src/sans_webapp/components/sidebar.py` lines 166-170
  - Input type: `st.text_input(..., type='password')`
  - Storage: Session state variable `st.session_state.chat_api_key`
  - Scope: AI chat and model suggestion features only
  - Fallback: Heuristic-based suggestions work without API key

**No user authentication system:**
- Application is public/unauthenticated
- No login/registration
- No role-based access control

## Monitoring & Observability

**Error Tracking:**
- None - No external error tracking service
- Local error handling in try/except blocks
- Streamlit UI error display: `st.error()`, `st.warning()`

**Logs:**
- Local stdout/stderr only
  - Streamlit logs to console during development
  - Docker logs captured via container runtime

## CI/CD & Deployment

**Hosting Targets:**
- Streamlit Cloud - Direct GitHub integration
- Docker - Containerized deployment
  - Dockerfile: `C:\Users\piotr\projects\ai\SANS-webapp\Dockerfile`
  - Registry: None configured (self-hosted or container registry needed)
- Heroku - PaaS deployment
  - Procfile: `web: streamlit run src/sans_webapp/app.py --server.port=$PORT --server.address=0.0.0.0`
- Custom servers - Docker or direct Python execution

**CI Pipeline:**
- GitHub Actions workflow present: `.github/workflows/`
  - Badge in README indicates test workflow: `tests.yml`
  - Runs: `pytest tests/ -v`
- Pre-commit hooks: `.pre-commit-config.yaml`
  - Ruff lint and format checks
  - Runs on commit before push

## Environment Configuration

**Required Environment Variables:**
- None strictly required
- Optional:
  - `OPENAI_API_KEY` - OpenAI API key (mentioned in README as environment variable option)
    - If set, loaded by OpenAI SDK automatically
    - User can override via UI input

**Secrets Location:**
- No `.env` file in repo
- Secrets management:
  - Streamlit Cloud: Use "Secrets" panel in app settings
  - Docker: Pass via environment variables during container startup
  - Heroku: Use Config Vars
  - Local development: Manual API key input via UI or environment variable

## Webhooks & Callbacks

**Incoming Webhooks:**
- None

**Outgoing Webhooks/Callbacks:**
- None - Unidirectional API calls only
- OpenAI API calls are synchronous request/response (no callbacks)

## Data Flow

**User → OpenAI Integration:**
1. User uploads SANS data (`src/sans_webapp/components/sidebar.py` lines 95-141)
2. User selects "AI-Assisted" model selection mode
3. User enters OpenAI API key via `st.text_input()` (line 166-170)
4. User clicks "Get Suggestions" button (line 175)
5. App calls `suggest_models_ai()` with data and API key (`src/sans_webapp/services/ai_chat.py` line 121-138)
6. Function analyzes data and creates prompt
7. Calls `create_chat_completion()` with `gpt-4o` model (`openai_client.py` line 28-35)
8. OpenAI API returns model suggestions
9. Suggestions displayed in selectbox for user to choose

**Chat Flow:**
1. User enters message in chat input area (`src/sans_webapp/components/sidebar.py` line 246-251)
2. User clicks "Send" button (line 257)
3. App calls `send_chat_message()` with message, API key, and fitter context (`services/ai_chat.py` line 23-118)
4. Function builds system prompt with current SANS data/model state
5. Calls `create_chat_completion()` with gpt-4o
6. Response added to chat history in session state
7. Chat history displayed to user

## File Format Support

**Input Formats:**
- CSV files - SANS data with Q, I, dI columns (standard)
- .dat files - Alternative SANS data format
- Handled by `sans_fitter.SANSFitter.load_data()`

**Output Formats:**
- CSV - Exported results (referenced in README: "Export Results: Save fitted parameters and curves to CSV")
- Interactive plots (Plotly) - Download-able as PNG/SVG

## Third-Party Libraries with External Calls

**SasModels:**
- Local library usage - No external calls
- Models downloaded/bundled during installation
- Used for model calculations via `DirectModel`

**BUMPS/LMFit:**
- Local optimization engines - No external calls
- BUMPS selected as default fitting engine
- LMFit available as alternative in UI

---

*Integration audit: 2026-02-04*
