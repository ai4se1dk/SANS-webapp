# SANS Data Analysis Web Application

A Streamlit-based web application for Small Angle Neutron Scattering (SANS) data analysis with AI-assisted model selection and interactive visualization.

## Features

### 📤 Data Upload
- Support for CSV and .dat file formats
- Expected columns: Q (scattering vector), I(Q) (intensity), dI(Q) (error)
- Built-in example dataset for testing
- Automatic data validation and preview

### 🎯 Model Selection
**Manual Mode:**
- Browse all available models from the SasModels library
- Comprehensive dropdown with 79+ models
- Categories include spherical, cylindrical, ellipsoidal, lamellar, and complex shapes

**AI-Assisted Mode:**
- Intelligent model suggestions based on data characteristics
- Uses OpenAI API for advanced analysis (optional)
- Built-in heuristic algorithm for offline suggestions
- Analyzes power-law slopes, Q-range, and intensity decay patterns

### ⚙️ Parameter Configuration
- Interactive parameter editing with Streamlit UI
- Set initial values, minimum/maximum bounds
- Select which parameters to fit (vary) or hold constant
- Quick presets: "Fit Scale & Background", "Fit All", "Fix All"
- Real-time parameter validation

### 🔬 Polydispersity Support
- Account for size distributions in real samples
- Tabbed interface: "Basic Parameters" | "Polydispersity"
- Master toggle to enable/disable polydispersity globally
- Configure per-parameter: width, distribution type, number of points
- Supported distributions: Gaussian, Lognormal, Schulz, Rectangle, Boltzmann
- Fit polydispersity width as a free parameter

### 🚀 Fitting Engines
**BUMPS** (Bayesian uncertainty modeling for parameter estimation)
- Methods: amoeba (Nelder-Mead), lm (Levenberg-Marquardt), newton, de (Differential Evolution)

**LMFit** (Non-linear least-squares minimization)
- Methods: leastsq, least_squares, differential_evolution, powell, nelder

### 📊 Visualization
- Interactive Plotly charts with zoom, pan, export
- Log-log scale for SANS data
- Data points with error bars
- Fitted curve overlay
- Real-time plot updates

### 💾 Results Export
- Download fitted parameters as CSV
- Includes parameter values, bounds, and fit status
- Ready for further analysis or reporting

## Installation

### Option 1: Basic Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/ai4se1dk/SANS-webapp.git
cd SANS-webapp

# Install the package
pip install -e .

# Run the web application (choose one method)
sans-webapp              # CLI command (recommended)
python -m sans_webapp    # Module execution
```

### Option 2: Development Installation

```bash
# Clone the repository
git clone https://github.com/ai4se1dk/SANS-webapp.git
cd SANS-webapp

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the web application
sans-webapp
```

### Option 3: Using Pixi

```bash
# Clone the repository
git clone https://github.com/ai4se1dk/SANS-webapp.git
cd SANS-webapp

# Install dependencies
pixi install

# Run the web application
pixi run app
```

### Option 4: Install from PyPI

```bash
# Install directly from PyPI
pip install sans-webapp

# Run the application
sans-webapp
```

## Quick Start Guide

### 1. Launch the Application

```bash
sans-webapp
```

Or alternatively:
```bash
python -m sans_webapp
```

The application will automatically open in your default web browser at `http://localhost:8501`.

### 2. Upload Your Data

**Option A: Use Example Data**
- Click "Load Example Data" button in the sidebar
- This loads bundled sample SANS data from the package

**Option B: Upload Your Own Data**
- Click "Browse files" in the sidebar
- Select your CSV or .dat file
- File must contain three columns: Q, I(Q), dI(Q)

**Data Format Example:**
```csv
Q,I,dI
0.001,1.035,0.020
0.006,0.990,0.020
0.011,1.038,0.020
...
```

### 3. Select a Model

**Manual Selection:**
1. Select "Manual" radio button
2. Choose model from dropdown (e.g., "sphere", "cylinder", "core_shell_sphere")
3. Click "Load Model"

**AI-Assisted Selection:**
1. Select "AI-Assisted" radio button
2. (Optional) Enter OpenAI API key for enhanced suggestions
3. Click "Get AI Suggestions"
4. Choose from suggested models
5. Click "Load Model"

### 4. Configure Parameters

- Review displayed parameters for the selected model
- For each parameter:
  - Set initial **Value**
  - Define **Min** and **Max** bounds
  - Check **Fit?** to include in optimization
- Use quick presets to configure multiple parameters at once
- Click "Update Parameters" to apply changes

**Recommended Starting Configuration:**
- Enable fitting for: `scale`, `background`, and 1-2 shape parameters
- Keep other parameters fixed initially
- Gradually enable more parameters if needed

### 5. Configure Polydispersity (Optional)

For samples with size distributions, use the Polydispersity tab:

1. **Click the "Polydispersity" tab** next to "Basic Parameters"
2. **Check "Enable Polydispersity"** to activate size distribution modeling
3. **Configure polydisperse parameters** in the table:

| Column | Description | Typical Values |
|--------|-------------|----------------|
| **Parameter** | Size parameter name (e.g., radius, length) | Read-only |
| **PD Width** | Relative width of distribution (0 = monodisperse) | 0.05-0.20 (5-20%) |
| **N Points** | Gaussian quadrature points (accuracy vs speed) | 35 (default) |
| **Type** | Distribution shape | gaussian, lognormal, schulz |
| **Vary** | Fit the PD width during optimization | ☑ to fit |

4. **Click "Update PD Parameters"** to apply changes

**Distribution Types Explained:**
- **Gaussian**: Symmetric bell curve, good for narrow distributions
- **Lognormal**: Skewed toward smaller sizes, prevents negative values (recommended for particle sizes)
- **Schulz**: Common in polymer science, similar to lognormal
- **Rectangle**: Uniform distribution within a range
- **Boltzmann**: For thermally activated size distributions

**Tips:**
- Start with 10% polydispersity (PD Width = 0.1)
- Keep PD Width fixed initially, then try fitting it
- Higher N Points = more accurate but slower fitting
- Models without size parameters won't show the Polydispersity tab

### 6. Run the Fit

1. Select optimization engine (BUMPS or LMFit)
2. Choose optimization method (e.g., "amoeba" for BUMPS)
3. Click "🚀 Run Fit"
4. Wait for optimization to complete (progress shown)

**Note:** Fitting with polydispersity enabled takes longer due to numerical integration over the size distribution.

### 7. View and Export Results

- Interactive plot shows data points and fitted curve
- Fitted parameter values displayed in table (includes PD parameters when enabled)
- Click "Save Results to CSV" to export
- Download CSV file with all parameter information

## Polydispersity Guide

### What is Polydispersity?

In real SANS experiments, particles are rarely perfectly uniform in size. **Polydispersity** accounts for this size distribution, providing more realistic fits to experimental data.

For example, a sample of spherical nanoparticles with a mean radius of 50 Å and 10% polydispersity has particles ranging roughly from 35-65 Å following a distribution curve.

### When to Use Polydispersity

**Use polydispersity when:**
- Your sample has a known size distribution
- Monodisperse fits show systematic residual patterns
- Fit quality improves significantly with PD enabled
- Working with colloids, polymers, or synthesized nanoparticles

**Skip polydispersity when:**
- Your sample is highly monodisperse (e.g., proteins, viruses)
- You're doing initial exploratory fits
- Fitting is already computationally slow

### Understanding PD Parameters

```
Parameter: radius
├── radius        = 50.0 Å    (mean size)
├── radius_pd     = 0.10      (10% relative width)
├── radius_pd_n   = 35        (quadrature points)
├── radius_pd_type = gaussian  (distribution shape)
└── radius_pd_nsigma = 3.0    (integration range)
```

**PD Width Interpretation:**
- `pd_width = 0.0`: Perfectly monodisperse (no size distribution)
- `pd_width = 0.1`: 10% polydispersity (typical for well-synthesized particles)
- `pd_width = 0.2`: 20% polydispersity (broader distribution)
- `pd_width > 0.3`: Very broad distribution (may need different model)

### Polydispersity Workflow Example

```
1. Load data and select model (e.g., sphere)
2. Fit without polydispersity first → Get baseline chi²
3. Enable polydispersity, set radius_pd = 0.1 (fixed)
4. Fit again → Compare chi² improvement
5. If improved, try fitting radius_pd as a free parameter
6. Final fit: Check if radius_pd value is physically reasonable
```

### Multiple Polydisperse Parameters

Some models have multiple size parameters that can be polydisperse:

| Model | Polydisperse Parameters |
|-------|-------------------------|
| sphere | radius |
| cylinder | radius, length |
| ellipsoid | radius_polar, radius_equatorial |
| core_shell_sphere | radius, thickness |

**Recommendation:** Start with polydispersity on the most important size parameter only, then add others if needed.

## Model Selection Guide

### Common SANS Models

**Spherical Particles:**
- `sphere` - Simple spherical particles
- `core_shell_sphere` - Sphere with shell structure
- `fuzzy_sphere` - Sphere with diffuse interface
- `vesicle` - Hollow spherical shell

**Cylindrical Particles:**
- `cylinder` - Simple cylindrical shape
- `core_shell_cylinder` - Cylinder with shell
- `flexible_cylinder` - Semi-flexible polymer chain
- `elliptical_cylinder` - Cylinder with elliptical cross-section

**Ellipsoidal Particles:**
- `ellipsoid` - Simple ellipsoidal shape
- `core_shell_ellipsoid` - Ellipsoid with shell
- `triaxial_ellipsoid` - Three different axes

**Lamellar/Flat Structures:**
- `lamellar` - Stacked layers
- `core_shell_lamellar` - Layered structure with shell
- `parallelepiped` - Rectangular box shape

**Complex Structures:**
- `fractal` - Fractal aggregates
- `pearl_necklace` - Polymer with clusters
- `flexible_cylinder_elliptical` - Complex flexible shapes

### AI Suggestion Algorithm

The built-in heuristic algorithm analyzes:
- **Power-law slope**: Determines particle shape (steep = spherical, gentle = flat)
- **Q-range**: Identifies size scales
- **Intensity decay**: Indicates structure complexity

For enhanced suggestions with OpenAI API:
- Analyzes complete data patterns
- Considers multiple features simultaneously
- Provides context-aware recommendations
- Returns 3-5 best-fit models

## Advanced Usage

### Customizing the Application

Edit `src/app.py` to customize:
- Default parameter values
- Optimization settings
- Plot styling and layout
- Additional model constraints

### Using with Structure Factors

While the web app focuses on form factors, you can extend it to include structure factors:

```python
# In your local modifications
fitter.set_structure_factor('hardsphere', radius_effective_mode='link_radius')
```

### Batch Processing

For analyzing multiple datasets:
1. Save your fitted parameters
2. Load next dataset
3. Use saved parameters as starting point
4. Repeat fitting process

## Deployment

### Streamlit Cloud (Free Hosting)

1. Push repository to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app"
5. Select repository: `ai4se1dk/SANS-webapp`
6. Main file: `src/sans_webapp/app.py`
7. Click "Deploy"

Your app will be available at `https://your-app-name.streamlit.app`

### Heroku Deployment

The `Procfile` and `setup.sh` are already configured for Heroku deployment.

Deploy:
```bash
heroku create your-app-name
git push heroku main
heroku open
```

### Docker Deployment

A `Dockerfile` is already included in the repository.

Build and run:
```bash
docker build -t sans-webapp-app .
docker run -p 8501:8501 sans-webapp-app
```

Access at `http://localhost:8501`

## API Key Management

### OpenAI API (Optional)

For AI-powered model suggestions:

1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Create an API key
3. Use in one of three ways:

**Method 1: Enter in UI** (Recommended)
- Paste key in sidebar text input
- Key stored in session only (not saved)

**Method 2: Environment Variable**
```bash
export OPENAI_API_KEY=your-key-here
sans-webapp
```

**Method 3: .env File**
```bash
echo "OPENAI_API_KEY=your-key-here" > .env
```

**Note**: The app works without API key using heuristic suggestions.

## Troubleshooting

### Common Issues

**1. Data Upload Fails**
- Check file format: Must be CSV or .dat
- Verify columns: Q, I(Q), dI(Q) required
- Check for missing values or NaN

**2. Model Load Error**
- Ensure SasModels is properly installed
- Try: `pip install --upgrade sasmodels`
- Check model name spelling

**3. Fitting Fails**
- Ensure at least one parameter has "Vary" enabled
- Check parameter bounds (min < value < max)
- Try different optimization method
- Reduce number of varying parameters

**4. Polydispersity Issues**
- PD Width > 0.5 may cause numerical instability
- Reduce `pd_n` (e.g., to 20) if fitting is too slow
- Some distribution types may not converge for all parameters
- Try Gaussian first, then switch to lognormal if needed

**5. Slow Performance**
- Large datasets (>1000 points) may be slow
- Use "amoeba" method for faster results
- Consider downsampling data
- With polydispersity: reduce `pd_n` or disable PD for initial fits

**6. Plot Not Displaying**
- Check browser console for errors
- Clear browser cache
- Try different browser

### Getting Help

- **Documentation**: See main [README.md](README.md)
- **Issues**: Report at [GitHub Issues](https://github.com/ai4se1dk/SANS-webapp/issues)
- **Tests**: Run `pytest tests/` for validation

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Code Style

```bash
# Using Pixi
pixi run lint
pixi run format

# Using pip
pip install ruff
ruff check . --fix
ruff format .
```

### Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## File Structure

```
SANS-webapp/
├── src/
│   └── sans_webapp/            # Main Python package
│       ├── __init__.py         # Package init with version
│       ├── __main__.py         # Entry point for CLI & module execution
│       ├── app.py              # Main Streamlit application
│       ├── demo_app.py         # Command-line demo
│       ├── openai_client.py    # OpenAI API wrapper
│       ├── sans_analysis_utils.py  # Shared utility functions
│       ├── sans_types.py       # TypedDict definitions
│       ├── ui_constants.py     # UI string constants
│       ├── data/               # Bundled example data
│       │   └── simulated_sans_data.csv
│       ├── components/         # UI rendering components
│       │   ├── __init__.py
│       │   ├── data_preview.py
│       │   ├── fit_results.py
│       │   ├── parameters.py
│       │   └── sidebar.py
│       └── services/           # Business logic services
│           ├── __init__.py
│           ├── ai_chat.py
│           └── session_state.py
├── tests/
│   └── test_app.py             # Unit tests (34 tests)
├── pyproject.toml              # Package configuration with CLI entry point
├── simulated_sans_data.csv     # Example data (also bundled in package)
├── Dockerfile                  # Docker deployment
├── Procfile                    # Heroku deployment
├── README.md                   # Main documentation
└── WEBAPP_README.md            # This file
```

## License

BSD 3-Clause License. See [LICENSE](LICENSE) for details.

## References

- **SasModels**: https://github.com/SasView/sasmodels
- **BUMPS**: https://github.com/bumps/bumps
- **Streamlit**: https://streamlit.io
- **Plotly**: https://plotly.com/python/
- **OpenAI**: https://openai.com

## Acknowledgments

Built on top of the excellent SasModels and BUMPS libraries from the SasView project.
