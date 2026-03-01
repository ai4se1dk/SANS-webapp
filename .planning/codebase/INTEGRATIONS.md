# External Integrations

**Analysis Date:** 2026-02-05

## APIs & External Services

**Anthropic Claude API:**
- **Service:** Claude AI model for SANS analysis assistance
- **What it's used for:** Intelligent model suggestions, interactive chat with MCP tool execution, parameter recommendations
- SDK/Client: `anthropic` package (1.0.0+)
- Auth: `ANTHROPIC_API_KEY` environment variable
- Model: `claude-sonnet-4-20250514` (via `ClaudeMCPClient` in `src/sans_webapp/services/claude_mcp_client.py`)
- Integration points:
  - `src/sans_webapp/services/claude_mcp_client.py` - Main Claude client with tool-use support
  - `src/sans_webapp/services/ai_chat.py` - Chat functions that route to Claude
  - `src/sans_webapp/mcp_server.py` - MCP tool definitions
  - `src/sans_webapp/app.py` - UI integration in right sidebar chat column

**OpenAI API (Legacy):**
- **Service:** OpenAI GPT-4o for fallback suggestions
- **What it's used for:** Model suggestions when AI tools disabled or as fallback
- SDK/Client: `openai` package (1.0.0+)
- Auth: Not currently configured (legacy code path)
- Model: `gpt-4o`
- Integration point: `src/sans_webapp/openai_client.py`, `src/sans_webapp/services/ai_chat.py` (_send_chat_message_openai function)

**SasModels Online:**
- **Service:** Implicit dependency for accessing physical scattering model definitions
- **What it's used for:** Database of 100+ SANS models (sphere, cylinder, ellipsoid, etc.)
- Client: `sasmodels` package (1.0+)
- No API key needed (local library)

## Data Storage

**Databases:**
- None - application is stateless per session
- Session state: Stored in Streamlit's in-memory session_state during a session
- No persistent database backend

**File Storage:**
- **Local filesystem only** - uploaded CSV/DAT files processed in memory
- Data file format: CSV or .dat (SANS ASCII format with Q, I, dI columns)
- Example dataset bundled: `src/sans_webapp/data/simulated_sans_data.csv` (included in package)
- Fit results: Exported by user as CSV download (no server-side storage)

**Caching:**
- None configured
- Each session processes data independently

## Authentication & Identity

**Auth Provider:**
- Custom API key management (no OAuth)
- Single API key per session (ANTHROPIC_API_KEY)
- Authentication approach:
  - Environment variable: `ANTHROPIC_API_KEY` (production)
  - Streamlit sidebar widget: Chat API key input field (runtime configuration)
  - No user authentication - single-session access

**Key Management:**
- `.env.template` provided as template (do NOT commit actual .env)
- Keys passed to:
  - `Anthropic(api_key=...)` constructor in `ClaudeMCPClient.__init__`
  - Stored in `st.session_state.chat_api_key` for UI access

## Monitoring & Observability

**Error Tracking:**
- None detected - no Sentry, Rollbar, or similar
- Errors logged to browser console and Streamlit UI
- Try-catch blocks throughout with user-facing error messages

**Logs:**
- Streamlit output to console (development)
- Docker container logs available when deployed
- No persistent log aggregation

## CI/CD & Deployment

**Hosting:**
- GitHub Actions CI/CD defined in `.github/workflows/`
- Deployment targets supported:
  - Docker (Dockerfile provided)
  - Heroku (Procfile configured for Streamlit)
  - Streamlit Cloud (native support)
  - Any environment with Python 3.10+

**CI Pipeline:**
- `.github/workflows/tests.yml` - Pytest execution on push
- `.github/workflows/ci.yml` - Additional CI checks
- `.github/workflows/codacy-coverage-reporter.yml` - Code coverage reporting to Codacy

**Container:**
- Dockerfile: `src/sans_webapp/app.py` as entry point
- Port mapping: 8501 (Streamlit)
- Health check: `curl --fail http://localhost:8501/_stcore/health`

## Environment Configuration

**Required env vars:**
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude (optional for basic app, required for AI assistant)

**Optional/Advanced:**
- `STREAMLIT_SERVER_PORT` - Override default 8501 (not needed, configured in Dockerfile CMD)
- `STREAMLIT_SERVER_ADDRESS` - Bind address (set to 0.0.0.0 in Docker)

**Secrets location:**
- `.env` file (git-ignored, created from `.env.template`)
- Environment variables in deployment platform
- Never committed to version control

**Config file locations:**
- `pyproject.toml` - Project-wide settings, tool configs
- `pixi.lock` - Environment lock for reproducibility

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

**MCP Tools (Claude Integration):**
The application exposes these MCP tools to Claude (defined in `src/sans_webapp/mcp_server.py` and `src/sans_webapp/services/claude_mcp_client.py`):

1. **list-sans-models** - List all 100+ available SANS models
2. **get-model-parameters** - Fetch parameter details for a specific model
3. **get-current-state** - Retrieve current fitter state (data, model, parameters)
4. **get-fit-results** - Fetch results from the most recent fit
5. **set-model** - Load a SANS model for fitting
6. **set-parameter** - Adjust parameter value, bounds, or vary flag
7. **set-multiple-parameters** - Batch set multiple parameters
8. **enable-polydispersity** - Enable size distribution for a parameter
9. **set-structure-factor** - Add interparticle interaction model
10. **remove-structure-factor** - Remove structure factor
11. **run-fit** - Execute curve fitting optimization

Tool execution flow:
- Claude initiates tool calls via Anthropic API
- `ClaudeMCPClient.chat()` intercepts tool_use stop_reason
- `execute_tool()` dispatches to handler in `mcp_server.py`
- Results returned to Claude for interpretation and next action
- Session state updates reflected in UI

## Data Integration Points

**Input:**
- CSV files (Q, I, dI columns)
- .dat files (SANS ASCII format)
- Uploaded via Streamlit file uploader in sidebar

**Output:**
- Fit results: CSV download (parameters, uncertainties, fit statistics)
- Plots: Interactive Plotly visualizations in browser (not persisted)
- Claude chat: Real-time responses in right sidebar

---

*Integration audit: 2026-02-05*
