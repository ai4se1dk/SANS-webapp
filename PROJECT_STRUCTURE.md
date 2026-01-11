# Complete Project Structure - SANS Data Analysis Web Application

This document describes all files added for the Streamlit web application.

## New Files Created

### Core Application Files

#### `src/app.py` (Main Application)
- **Purpose**: Main Streamlit web application
- **Lines**: ~550 lines
- **Key Features**:
  - Data upload (CSV, .dat files)
  - Manual model selection from 79+ SasModels
  - AI-assisted model suggestion (with OpenAI API or heuristics)
  - Interactive parameter configuration with Streamlit UI
  - Real-time fitting with BUMPS and LMFit engines
  - Interactive Plotly visualization
  - CSV export of results
- **Dependencies**: streamlit, plotly, pandas, numpy, openai, sasmodels, sans_fitter, sans_analysis_utils
- **Run**: `streamlit run src/app.py`

#### `src/sans_analysis_utils.py` (Shared Utilities)
- **Purpose**: Shared utility functions for SANS data analysis
- **Lines**: ~140 lines
- **Key Functions**:
  - `get_all_models()` - Fetch available models from sasmodels
  - `analyze_data_for_ai_suggestion()` - Analyze data characteristics for model suggestion
  - `suggest_models_simple()` - Heuristic-based model suggestion
  - `plot_data_and_fit()` - Create interactive Plotly visualizations
- **Dependencies**: numpy, plotly, sasmodels (no Streamlit dependency)
- **Usage**: Imported by both `app.py` and `demo_app.py`

### Testing & Demo Files

#### `tests/test_app.py`
- **Purpose**: Automated test suite for web app and utilities functionality
- **Tests**:
  - Utility functions (model listing, data analysis, suggestions, plotting)
  - SANSFitter integration
  - App module imports
- **Run**: `python tests/test_app.py`
- **Output**: Pass/fail status for all core features

#### `src/demo_app.py`
- **Purpose**: Command-line demonstration of complete workflow
- **Shows**:
  - Model selection (79 available)
  - Data loading
  - AI-assisted suggestions
  - Parameter configuration
  - Fitting process (with real optimization)
  - Results export
- **Run**: `python src/demo_app.py`
- **Duration**: ~10-30 seconds

### Documentation Files

#### `WEBAPP_README.md`
- **Purpose**: Comprehensive web application documentation
- **Sections**:
  - Features overview
  - Installation instructions (3 methods)
  - Quick start guide with screenshots
  - Model selection guide (categorized)
  - Advanced usage
  - Deployment options (Streamlit Cloud, Heroku, Docker)
  - API key management
  - Troubleshooting
- **Length**: ~350 lines

#### `QUICKSTART.md`
- **Purpose**: Quick reference guide
- **Sections**:
  - 3-step installation
  - 5-step usage workflow
  - Common models table
  - Deployment commands
  - Troubleshooting tips
- **Length**: ~150 lines

#### `README.md` (Updated)
- **Changes**: Added new section "Web Application"
- **Addition**: ~70 lines covering:
  - Web app features
  - Quick start commands
  - Deployment options
  - API integration

### Deployment Files

#### `Dockerfile`
- **Purpose**: Containerized deployment
- **Base Image**: python:3.10-slim
- **Includes**: System dependencies (gcc, gfortran), all Python packages
- **Exposes**: Port 8501
- **Build**: `docker build -t sans-app .`
- **Run**: `docker run -p 8501:8501 sans-app`

#### `Procfile`
- **Purpose**: Heroku deployment configuration
- **Command**: Runs Streamlit with dynamic port binding
- **Deploy**: `git push heroku main`

#### `setup.sh`
- **Purpose**: Streamlit configuration for Heroku
- **Creates**: `~/.streamlit/config.toml` and `credentials.toml`
- **Config**: Headless mode, CORS settings, dynamic port

### Data Files

#### `example_sans_data.dat`
- **Purpose**: Example dataset for testing
- **Format**: Three columns (Q, I, dI)
- **Points**: 70 data points
- **Q Range**: 0.001 to 0.347 Å⁻¹
- **Use**: Alternative to simulated_sans_data.csv

#### `simulated_sans_data.csv`
- **Purpose**: Primary example dataset
- **Points**: 200 data points
- **Q Range**: 0.001 to 1.0 Å⁻¹

## Key Features Implemented

### 1. Data Upload ✓
- Drag-and-drop file upload
- Support for CSV and .dat formats
- Example data loading
- Data validation and preview

### 2. Model Selection ✓
- Manual: 79+ models from SasModels
- AI-Assisted: Heuristic-based suggestions
- AI-Assisted: OpenAI API integration (optional)
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

### Installation
```bash
pip install -e .              # Install package with all dependencies
streamlit run src/app.py      # Launch application
```

## API Integration

### OpenAI API (Optional)
- **Purpose**: Enhanced AI model suggestions
- **Cost**: Pay-per-use pricing
- **Fallback**: Built-in heuristic suggestions work without API key
- **Privacy**: API key not stored, session-only

## Next Steps for Users

1. **Try the app**: `streamlit run src/app.py`
2. **Run demo**: `python src/demo_app.py`
3. **Read docs**: Check WEBAPP_README.md
4. **Deploy**: Choose Streamlit Cloud, Heroku, or Docker
5. **Contribute**: Submit issues or PRs on GitHub

## License

All new code follows the existing BSD 3-Clause License.
