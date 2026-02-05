# SANS Model Fitter

[![Tests](https://github.com/ai4se1dk/SANS-webapp/actions/workflows/tests.yml/badge.svg)](https://github.com/ai4se1dk/SANS-webapp/actions/workflows/tests.yml)
[![PyPI badge](https://img.shields.io/pypi/v/sans-webapp.svg)](https://pypi.python.org/pypi/sans-webapp)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/e12661e2850746388568eff743de22a2)](https://app.codacy.com/gh/ai4se1dk/SANS-webapp/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

## SANS-webapp

A Streamlit-based web application is now available for interactive SANS data analysis with a user-friendly interface.

### Features

- 📤 **Data Upload**: Upload your SANS datasets (CSV or .dat files)
- 🤖 **AI-Assisted Model Selection**: Get intelligent model suggestions based on your data
- 🎯 **Manual Model Selection**: Choose from all available SasModels
- ⚙️ **Interactive Parameter Tuning**: Adjust parameters with real-time UI controls
- 📊 **Interactive Plots**: Visualize data and fits with Plotly's zoom, pan, and export features
- 💾 **Export Results**: Save fitted parameters and curves to CSV

### Quick Start (Web App)

```bash
# Install the application
pip install -e .

# Run the Streamlit app (choose one)
sans-webapp              # CLI command
python -m sans_webapp    # Module execution
```

The app will open in your browser at `http://localhost:8501`.

### Install from PyPI

```bash
pip install sans-webapp
sans-webapp
```

### Using the Web Application

1. **Upload Data**: Use the sidebar to upload your SANS data file (CSV or .dat format with Q, I, dI columns) or load the example dataset
2. **Select Model**: 
   - **Manual**: Choose from dropdown of all SasModels models
   - **AI-Assisted**: Optionally provide an Anthropic (Claude) API key for AI-powered suggestions and MCP tool access, or use built-in heuristics
3. **Configure Parameters**: Set initial values, bounds, and which parameters to fit
4. **Run Fit**: Choose optimization engine (BUMPS or LMFit) and method, then click "Run Fit"
5. **View Results**: Interactive plots show data with error bars and fitted curve
6. **Export**: Download fitted parameters as CSV

### Web App Deployment

#### Streamlit Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and deploy from the repository
4. Set `src/sans_webapp/app.py` as the main file

#### Heroku

```bash
# The Procfile is already configured
# Deploy directly
heroku create your-app-name
git push heroku main
```

#### Docker

```bash
# Build image
docker build -t SANS-webapp-app .

# Run container
docker run -p 8501:8501 SANS-webapp-app
```

### API Integration

The web app supports optional AI-powered model suggestions and MCP tool usage via Anthropic (Claude):

1. Get an API key from Anthropic (https://console.anthropic.com/)
2. Enter the key in the sidebar when using AI-Assisted mode
3. Or set as environment variable: `export ANTHROPIC_API_KEY=your-key-here`

**Note**: The app also works without an API key using built-in heuristic suggestions.

## License

BSD 3-Clause License. See [LICENSE](LICENSE) for the full text.

## References

- SasModels: https://github.com/SasView/sasmodels
- BUMPS: https://github.com/bumps/bumps
- LMFit: https://lmfit.github.io/lmfit-py/
- Streamlit: https://streamlit.io
- Plotly: https://plotly.com/python/
