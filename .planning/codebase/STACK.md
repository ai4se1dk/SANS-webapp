# Technology Stack

**Analysis Date:** 2026-02-04

## Languages

**Primary:**
- Python 3.10+ - Main language for backend, CLI, and web application
- HTML/CSS - Rendered by Streamlit framework

**Secondary:**
- YAML - Configuration files (pyproject.toml, pre-commit hooks)

## Runtime

**Environment:**
- Python 3.10+ (pinned in `pyproject.toml`: `requires-python = ">=3.10"`)
- CPython (verified in Dockerfile: `FROM python:3.10-slim`)

**Package Manager:**
- `pip` with setuptools (defined in `[build-system]` section)
- `pixi` for environment management (Conda-based, cross-platform: `platforms = ["win-64", "linux-64", "osx-64", "osx-arm64"]`)
- Lockfile: `pixi.lock` (present)

## Frameworks

**Core Web Framework:**
- Streamlit 1.28.0+ - Interactive web UI framework
  - Entry point: `src/sans_webapp/app.py`
  - Run command: `streamlit run src/sans_webapp/app.py`
  - Server port: 8501 (default, configurable)

**Scientific Computing:**
- SANS-Fitter 0.0.3+ - Custom package for SANS data analysis
  - Imported as: `from sans_fitter import SANSFitter, get_all_models`
  - Location: `src/sans_webapp/services/ai_chat.py`, `src/sans_webapp/components/*.py`
- SasModels 1.0+ - Small Angle Scattering models library
  - Imported as: `from sasmodels.direct_model import DirectModel`
  - Used for model calculations in `src/sans_webapp/services/ai_chat.py`
- SasData 0.8+ - SAS data handling
- BUMPS 0.9+ - Optimization engine for model fitting
  - Alternative: LMFit (referenced in UI but not in pyproject.toml as direct dependency)

**Visualization:**
- Plotly 5.17.0+ - Interactive plots
  - Location: `src/sans_webapp/sans_analysis_utils.py`
  - Used for data visualization with zoom, pan, export

**Data Processing:**
- NumPy 1.20+ - Numerical arrays
- Pandas 2.0.0+ - Data frames and CSV handling
- SciPy 1.7+ - Scientific computing utilities
- Matplotlib 3.5+ - Plotting (dependency of other packages)

**Testing:**
- Pytest 7.0+ - Test runner
  - Config: `[tool.pytest.ini_options]` in `pyproject.toml`
  - Test discovery: `testpaths = ["tests"]`
  - Run: `pytest tests/ -v`
- Pytest-Cov 4.0+ - Coverage reporting
  - Run: `pytest tests/ --cov=. --cov-report=html --cov-report=term --cov-report=xml`

**Build/Dev Tools:**
- Ruff 0.8.0+ - Linter and formatter (unified toolchain)
  - Config: `[tool.ruff]` section with line-length: 100, target-version: py39
  - Lint rules: E, W, F, I, B, C4, UP, Q
  - Run: `ruff check src/ tests/ --fix` and `ruff format src/ tests/`
- Pre-commit 2.17+ - Git hooks framework
  - Config file: `.pre-commit-config.yaml`
  - Hooks: Ruff linter and formatter on python/pyi/jupyter files

**AI/ML:**
- OpenAI 1.0.0+ - OpenAI API client
  - Location: `src/sans_webapp/openai_client.py`
  - Model: `gpt-4o` (hardcoded in `src/sans_webapp/services/ai_chat.py` line 107)

## Key Dependencies

**Critical (Scientific):**
- sans-fitter (0.0.3+) - Custom SANS analysis package
- sasmodels (1.0+) - Model library for scattering
- numpy (1.20+) - Numerical computations
- scipy (1.7+) - Scientific functions

**Infrastructure:**
- streamlit (1.28.0+) - Web UI framework
- plotly (5.17.0+) - Interactive visualizations
- pandas (2.0.0+) - Data manipulation
- openai (1.0.0+) - AI integration

**Optional:**
- mkdocs (1.5+) - Documentation generation (dev dependency)
- mkdocs-material (9.5+) - Material theme for docs
- mkdocstrings[python] (0.25+) - Python docstring extraction

## Configuration

**Environment:**
- No `.env` file detected in repo
- OpenAI API key: Passed via Streamlit input UI (not env-based)
  - Location: `src/sans_webapp/components/sidebar.py` line 166-170
  - Storage: Streamlit session state as `st.session_state.chat_api_key`
- Environment variables: No required env vars enforced (optional OPENAI_API_KEY mentioned in README)

**Build Configuration:**
- `pyproject.toml` - Main config (setuptools-based)
- `pixi.lock` - Reproducible environment lock
- `.pixi/envs/` - Pixi environment directory (contains conda packages)
- `setup.py` - Not present (using modern pyproject.toml)

**Pre-commit Hooks:**
- File: `.pre-commit-config.yaml`
- Hooks configured:
  - `ruff` with `--fix` flag
  - `ruff-format`
  - Files matched: `^(src|tests)/`

**Ruff Configuration Details:**
- Line length: 100 characters
- Quote style: Single quotes (`inline-quotes: "single"`)
- Per-file ignores: `__init__.py` (F401), `tests/*` (F401, F811)

## Platform Requirements

**Development:**
- Python 3.10+
- Compiler support: GCC, G++, Gfortran (for scientific packages)
  - Required in Dockerfile: `gcc`, `g++`, `gfortran`, `libgomp1`
- Git (for pre-commit hooks)
- Pixi or pip+setuptools

**Production:**
- Python 3.10+
- Deployment targets:
  - **Streamlit Cloud** - Direct GitHub integration
  - **Docker** - Containerized (Dockerfile present)
    - Base image: `python:3.10-slim`
    - Exposed port: 8501
    - Healthcheck: `curl --fail http://localhost:8501/_stcore/health`
  - **Heroku** - Procfile configured: `web: streamlit run src/sans_webapp/app.py --server.port=$PORT --server.address=0.0.0.0`

## System Dependencies

**Required for Scientific Computing:**
- GCC, G++, Gfortran (for NumPy, SciPy compilation)
- OpenMP library (`libgomp1`)

---

*Stack analysis: 2026-02-04*
