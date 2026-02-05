# Complete Project Structure - SANS Data Analysis Web Application

This document describes the pip-installable package structure for the Streamlit web application.

## Package Structure

The application is structured as a proper Python package (`sans_webapp`) that can be installed via pip and run with a simple CLI command.

### Installation & Usage

```bash
# Install from source
pip install -e .

# Or install from PyPI
pip install sans-webapp

# Run the application
sans-webapp              # CLI command
python -m sans_webapp    # Module execution
```

### Core Package Files

#### `src/sans_webapp/__init__.py` (Package Init)
- **Purpose**: Package initialization with version
- **Exports**: `__version__ = '0.0.1'`

#### `src/sans_webapp/__main__.py` (Entry Point)
- **Purpose**: Entry point for CLI and module execution
- **Function**: `main()` - launches Streamlit app
- **Usage**: `python -m sans_webapp` or `sans-webapp` CLI command

#### `src/sans_webapp/app.py` (Main Application)
- **Purpose**: Main Streamlit web application
- **Lines**: ~550 lines
- **Key Features**:
  - Data upload (CSV, .dat files)
  - Manual model selection from 79+ SasModels
  - AI-assisted model suggestion (with Anthropic (Claude) API or heuristics)
  - Interactive parameter configuration with Streamlit UI
  - Real-time fitting with BUMPS and LMFit engines
  - Interactive Plotly visualization
  - CSV export of results
- **Dependencies**: streamlit, plotly, pandas, numpy, anthropic, sasmodels, sans_fitter
- **Run**: `sans-webapp` or `python -m sans_webapp`

#### `src/sans_webapp/sans_analysis_utils.py` (Shared Utilities)
- **Purpose**: Shared utility functions for SANS data analysis
- **Lines**: ~140 lines
- **Key Functions**:
  - `get_all_models()` - Fetch available models from sasmodels
  - `analyze_data_for_ai_suggestion()` - Analyze data characteristics for model suggestion
  - `suggest_models_simple()` - Heuristic-based model suggestion
  - `plot_data_and_fit()` - Create interactive Plotly visualizations
- **Dependencies**: numpy, plotly, sasmodels (no Streamlit dependency)
- **Usage**: Imported by app.py and other modules

#### `src/sans_webapp/sans_types.py` (Type Definitions)
- **Purpose**: TypedDict definitions for type safety
- **Types**: `ParamInfo`, `FitResult`, `ParamUpdate`

#### `src/sans_webapp/ui_constants.py` (UI Constants)
- **Purpose**: All UI string constants centralized
- **Lines**: ~145 lines

#### `src/sans_webapp/openai_client.py` (Legacy OpenAI wrapper)
- **Purpose**: Legacy OpenAI API wrapper (kept for fallback behavior)

### Component Modules (`src/sans_webapp/components/`)

#### `data_preview.py`
- **Purpose**: Data visualization and preview section
- **Function**: `render_data_preview()`

#### `fit_results.py`
- **Purpose**: Fit results display, sliders, and export
- **Functions**: `render_fit_results()`, `_render_parameter_slider()`, etc.

#### `parameters.py`
- **Purpose**: Parameter table and preset management
- **Functions**: `render_parameters()`, `apply_param_updates()`, etc.

#### `sidebar.py`
- **Purpose**: Sidebar UI controls
- **Functions**: `render_data_upload_sidebar()`, `render_model_selection_sidebar()`, `render_ai_chat_sidebar()`

### Service Modules (`src/sans_webapp/services/`)

#### `session_state.py`
- **Purpose**: Streamlit session state management
- **Functions**: `initialize_session_state()`, `clear_parameter_state()`, etc.

#### `ai_chat.py`
- **Purpose**: AI chat and model suggestion service
- **Functions**: `send_message()`, `get_ai_suggestions()`

### Data Files

#### `src/sans_webapp/data/simulated_sans_data.csv`
- **Purpose**: Bundled example dataset (200 points)
- **Included in package**: Yes, via `package-data` in pyproject.toml

### Testing & Demo Files

#### `tests/test_app.py`
- **Purpose**: Automated test suite for package functionality
- **Tests**: 34 tests covering all modules
- **Run**: `pytest tests/ -v`
- **Output**: Pass/fail status for all core features

#### `src/sans_webapp/demo_app.py`
- **Purpose**: Command-line demonstration of complete workflow
- **Shows**:
  - Model selection (79 available)
  - Data loading
  - AI-assisted suggestions
  - Parameter configuration
  - Fitting process (with real optimization)
  - Results export
- **Run**: `python -m sans_webapp.demo_app`
- **Duration**: ~10-30 seconds

### Configuration Files

#### `pyproject.toml`
- **Purpose**: Package configuration with CLI entry point
- **Entry Point**: `sans-webapp = "sans_webapp.__main__:main"`
- **Package Discovery**: `where = ["src"]`
- **Package Data**: Includes `data/*.csv` files

### Documentation Files

#### `WEBAPP_README.md`
- **Purpose**: Comprehensive web application documentation
- **Sections**:
  - Features overview
  - Installation instructions (4 methods including PyPI)
  - Quick start guide
  - Model selection guide
  - Deployment options
  - Troubleshooting

#### `QUICKSTART.md`
- **Purpose**: Quick reference guide
- **Highlights**: CLI command `sans-webapp`, `python -m sans_webapp`

#### `PROJECT_STRUCTURE.md`
- **Purpose**: This file - documents package structure

#### `README.md`
- **Purpose**: Main project documentation with quick start

### Deployment Files

#### `Dockerfile`
- **Purpose**: Containerized deployment
- **Base Image**: python:3.10-slim
- **Command**: Uses `sans-webapp` CLI
- **Exposes**: Port 8501
- **Build**: `docker build -t sans-app .`
- **Run**: `docker run -p 8501:8501 sans-app`

#### `Procfile`
- **Purpose**: Heroku deployment configuration
- **Command**: `web: streamlit run src/sans_webapp/app.py --server.port=$PORT`
- **Deploy**: `git push heroku main`

#### `setup.sh`
- **Purpose**: Streamlit configuration for Heroku
- **Creates**: `~/.streamlit/config.toml` and `credentials.toml`
- **Config**: Headless mode, CORS settings, dynamic port

### External Data Files

#### `simulated_sans_data.csv`
- **Purpose**: Example dataset (also bundled inside package)
- **Points**: 200 data points
- **Q Range**: 0.001 to 1.0 Å⁻¹
- **Note**: The package includes this file in `src/sans_webapp/data/`

## Key Features Implemented

### 1. Pip-Installable Package ✓
- Install via `pip install sans-webapp`
- Run via `sans-webapp` CLI command
- Or `python -m sans_webapp`

### 2. Data Upload ✓
- Drag-and-drop file upload
- Support for CSV and .dat formats
- Example data loading
- Data validation and preview

### 2. Model Selection ✓
- Manual: 79+ models from SasModels
- AI-Assisted: Heuristic-based suggestions
- AI-Assisted: Anthropic (Claude) API integration (optional)
- Dynamic model loading

### 3. Parameter Configuration ✓
- Interactive UI with Streamlit inputs
- Value, min, max, vary for each parameter
- Quick presets (Fit All, Fix All, etc.)
- Real-time updates

### 4. Fitting ✓
- BUMPS engine (amoeba, lm, newton, de)
- LMFit engine (leastsq, least_squares, etc.)
- Progress indication
- Error handling

### 5. Visualization ✓
- Interactive Plotly charts
- Log-log scale
- Error bars
- Zoom, pan, export
- Fitted curve overlay

### 6. Results Export ✓
- CSV download
- All parameters with values and bounds
- Fit status for each parameter

### 7. Deployment ✓
- Docker support
- Heroku support
- Streamlit Cloud ready
- Environment configuration

## Testing Results

### Utility Functions Tests (`sans_analysis_utils.py`)
- ✓ Model listing (79 models found)
- ✓ Data analysis for AI suggestions
- ✓ Simple model suggestions
- ✓ Plot generation

### App Module Tests (`app.py`)
- ✓ Module imports successfully
- ✓ AI suggestion function available
- ✓ SANSFitter integration

### Demo Test (`src/demo_app.py`)
- ✓ Complete workflow executes
- ✓ Real fitting completes successfully
- ✓ Results export works

## Usage Statistics

### Installation & Running
```bash
# From source
pip install -e .          # Install package in editable mode
sans-webapp                # Launch application

# From PyPI
pip install sans-webapp    # Install from PyPI
sans-webapp                # Launch application

# Alternative
python -m sans_webapp      # Run as module
```

## API Integration

### Anthropic API (Optional)
- **Purpose**: Enhanced AI model suggestions and MCP tool access (Anthropic Claude)
- **Cost**: Pay-per-use pricing
- **Fallback**: Built-in heuristic suggestions work without API key
- **Privacy**: API key not stored, session-only

## Next Steps for Users

1. **Install**: `pip install sans-webapp` or `pip install -e .`
2. **Run the app**: `sans-webapp`
3. **Run demo**: `python -m sans_webapp.demo_app`
4. **Read docs**: Check WEBAPP_README.md
5. **Deploy**: Choose Streamlit Cloud, Heroku, or Docker
6. **Contribute**: Submit issues or PRs on GitHub

## License

All new code follows the existing BSD 3-Clause License.
