# SANS Model Fitter

[![Tests](https://github.com/ai4se1dk/SANS-webapp/actions/workflows/tests.yml/badge.svg)](https://github.com/ai4se1dk/SANS-webapp/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/ai4se1dk/SANS-webapp/graph/badge.svg)](https://codecov.io/gh/ai4se1dk/SANS-webapp)

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

# Run the Streamlit app
streamlit run src/app.py
```

The app will open in your browser at `http://localhost:8501`.

### Using the Web Application

1. **Upload Data**: Use the sidebar to upload your SANS data file (CSV or .dat format with Q, I, dI columns) or load the example dataset
2. **Select Model**: 
   - **Manual**: Choose from dropdown of all SasModels models
   - **AI-Assisted**: Optionally provide an OpenAI API key for AI-powered suggestions, or use built-in heuristics
3. **Configure Parameters**: Set initial values, bounds, and which parameters to fit
4. **Run Fit**: Choose optimization engine (BUMPS or LMFit) and method, then click "Run Fit"
5. **View Results**: Interactive plots show data with error bars and fitted curve
6. **Export**: Download fitted parameters as CSV

### Web App Deployment

#### Streamlit Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and deploy from the repository
4. Set `src/app.py` as the main file

#### Heroku

```bash
# Create Procfile
echo "web: streamlit run src/app.py --server.port=$PORT --server.address=0.0.0.0" > Procfile

# Deploy
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

The web app supports optional AI-powered model suggestions via the OpenAI API:

1. Get an API key from [platform.openai.com](https://platform.openai.com)
2. Enter the key in the sidebar when using AI-Assisted mode
3. Or set as environment variable: `export OPENAI_API_KEY=your-key-here`

**Note**: The app also works without an API key using built-in heuristic suggestions.

## License

BSD 3-Clause License. See [LICENSE](LICENSE) for the full text.

## References

- SasModels: https://github.com/SasView/sasmodels
- BUMPS: https://github.com/bumps/bumps
- LMFit: https://lmfit.github.io/lmfit-py/
- Streamlit: https://streamlit.io
- Plotly: https://plotly.com/python/
