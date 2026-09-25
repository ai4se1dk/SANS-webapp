"""
UI Constants for SANS webapp.

Contains all string constants used in the application UI,
making localization easier and keeping the main logic cleaner.
"""

# Maximum value that Streamlit's number_input can handle
MAX_FLOAT_DISPLAY = 1e300
MIN_FLOAT_DISPLAY = -1e300

# App Configuration
APP_PAGE_TITLE = 'SANS Data Analysis'
APP_PAGE_ICON = '🔬'
APP_LAYOUT = 'wide'
APP_SIDEBAR_STATE = 'expanded'
APP_TITLE = '🔬 SANS Data Analysis Web Application'
APP_SUBTITLE = (
    'Analyze Small Angle Neutron Scattering (SANS) data with model fitting and '
    'AI-assisted model selection.'
)

# Sidebar Headers
SIDEBAR_CONTROLS_HEADER = 'Controls'
SIDEBAR_DATA_UPLOAD_HEADER = 'Data Upload'
SIDEBAR_MODEL_SELECTION_HEADER = 'Model Selection'
SIDEBAR_FITTING_HEADER = 'Fitting'
SIDEBAR_ANALYSIS_FILES_HEADER = 'Save & Load'

# Upload Section
UPLOAD_LABEL = 'Upload SANS data file'
UPLOAD_TYPES = ['csv', 'dat', 'txt', 'abs', 'xml', 'h5', 'hdf5', 'nxs']
UPLOAD_HELP = (
    'Columnar text (Q, I(Q), dI(Q) and optionally dQ), CanSAS XML or NXcanSAS HDF5. '
    'Files are read through sasdata; the first dataset in a multi-dataset file is used.'
)
EXAMPLE_SELECT_LABEL = 'Example dataset'
EXAMPLE_SELECT_HELP = (
    'Measured and simulated datasets bundled with sans-fitter. Each loads with a '
    'suitable model and starting parameters, ready to fit.'
)
EXAMPLE_DEFAULT = 'sphere'
LOAD_EXAMPLE_BUTTON = 'Load Example'

# Save & Load (analysis files and report)
DOWNLOAD_ANALYSIS_BUTTON = '💾 Download analysis (.json)'
DOWNLOAD_REPORT_BUTTON = '📄 Download report (.html)'
ANALYSIS_SAVE_CAPTION = (
    'The analysis holds the model, parameters, polydispersity, links, resolution, '
    'Q range and the last fit (if nothing changed since). Parameter edits are saved '
    'once applied with "Update Parameters".'
)
ANALYSIS_UPLOAD_LABEL = 'Load a saved analysis'
ANALYSIS_UPLOAD_HELP = 'An analysis file downloaded from this app or written by sans-fitter.'
APPLY_ANALYSIS_BUTTON = 'Apply to loaded data'
ANALYSIS_NEEDS_DATA_INFO = 'Load the data first: a saved analysis is applied to the loaded data.'
SUCCESS_ANALYSIS_LOADED = 'Analysis loaded.'
SUCCESS_ANALYSIS_LOADED_WITH_FIT = 'Analysis loaded, including its fit result.'

# Resolution (instrument smearing)
RESOLUTION_HEADER = '**Resolution**'
RESOLUTION_MODE_LABEL = 'Resolution smearing'
RESOLUTION_MODES = {
    'data': 'From the data (dQ column)',
    'none': 'None',
    'pinhole': 'Pinhole (constant ΔQ/Q)',
}
RESOLUTION_MODE_HELP = (
    'How instrument resolution is applied when the model is evaluated. '
    '"From the data" uses the file\'s dQ column and evaluates unsmeared if there is none.'
)
RESOLUTION_DQ_LABEL = 'ΔQ/Q (σ, not FWHM)'
RESOLUTION_DQ_HELP = 'Relative Gaussian 1-σ width, the same quantity as a dQ column divided by Q.'
RESOLUTION_DQ_DEFAULT = 0.05
RESOLUTION_OTHER_MODE_CAPTION = 'Current setting: {mode} (set outside the app).'

SELECTION_METHOD_LABEL = 'Selection Method'
SELECTION_METHOD_OPTIONS = ['Manual', 'AI-Assisted']
SELECTION_METHOD_HELP = 'Choose how to select the fitting model'
MODEL_SELECT_LABEL = 'Select Model'
MODEL_SELECT_HELP = 'Choose a model from the sasmodels library'
AI_ASSISTED_HEADER = '**AI-Assisted Model Suggestion**'
AI_KEY_LABEL = 'Anthropic API Key (optional)'
AI_KEY_HELP = (
    'Enter your Anthropic (Claude) API key for AI-powered suggestions and MCP tool access. '
    'Leave empty to use heuristic suggestions or the legacy OpenAI fallback.'
)
AI_SUGGESTIONS_BUTTON = 'Get AI Suggestions'
AI_SUGGESTIONS_HEADER = '**Suggested Models:**'
AI_SUGGESTIONS_SELECT_LABEL = 'Choose from suggestions'
LOAD_MODEL_BUTTON = 'Load Model'

# Data Preview
DATA_PREVIEW_HEADER = '📊 Data Preview'
DATA_STATS_HEADER = '**Data Statistics**'
SHOW_DATA_TABLE_LABEL = 'Show data table'
DATA_TABLE_HEIGHT = 300
METRIC_DATA_POINTS = 'Data Points'
METRIC_Q_RANGE = 'Q Range'
METRIC_MAX_INTENSITY = 'Max Intensity'
METRIC_HAS_DI = 'dI column'
METRIC_HAS_DQ = 'dQ column'
METRIC_FIT_Q_RANGE = 'Fit Q Range'
METRIC_YES = 'yes'
METRIC_NO = 'no'
WARNING_NO_DI = (
    '⚠️ This dataset carries no intensity uncertainties (dI). The bumps engine cannot weight '
    'such points; use the lmfit engine (unweighted) or supply a dI column.'
)
DATA_FORMAT_HELP = """
### Expected Data Format

Your data file should be a columnar text file (CSV, .dat, .txt), a CanSAS XML file
or an NXcanSAS HDF5 file. Columnar files are read in the order Q, I(Q), dI(Q), dQ:
- **Q**: Scattering vector (Å⁻¹)
- **I(Q)**: Intensity (cm⁻¹)
- **dI(Q)**: Error/uncertainty in intensity (required for the bumps engine)
- **dQ**: Q resolution (optional; applied as pinhole smearing when present)

Example:
```
Q,I,dI
0.001,1.035,0.020
0.006,0.990,0.020
0.011,1.038,0.020
...
```
"""

# Parameters Section
PARAMETERS_HEADER_PREFIX = '⚙️ Model Parameters: '
PARAMETERS_HELP_TEXT = (
    'Configure the model parameters below. Set initial values, bounds, and whether each '
    'parameter\nshould be fitted (vary) or held constant.'
)
PARAMETER_COLUMNS_LABELS = ('**Parameter**', '**Value**', '**Min**', '**Max**', '**Fit?**')
PARAMETER_UPDATE_BUTTON = 'Update Parameters'
PARAMETER_VALUE_LABEL = 'Value'
PARAMETER_MIN_LABEL = 'Min'
PARAMETER_MAX_LABEL = 'Max'
PARAMETER_FIT_LABEL = 'Fit'
PRESET_HEADER = '**Quick Presets:**'
PRESET_FIT_SCALE_BACKGROUND = 'Fit Scale & Background'
PRESET_FIT_ALL = 'Fit All Parameters'
PRESET_FIX_ALL = 'Fix All Parameters'

# Parameter Tabs
PARAM_TAB_BASIC = '📊 Basic Parameters'
PARAM_TAB_POLYDISPERSITY = '📈 Polydispersity'
PARAM_TAB_ADVANCED = '⚙️ Advanced'

# Polydispersity Section
PD_NOT_SUPPORTED = 'ℹ️ This model does not support polydispersity.'
PD_ENABLE_LABEL = 'Enable Polydispersity'
PD_ENABLE_HELP = (
    'When enabled, polydispersity parameters are included in the model calculation. '
    'This accounts for size distribution in your sample.'
)
PD_AVAILABLE_PARAMS_LABEL = '**Polydisperse Parameters ({count} available)**'
PD_NO_PARAMS_CONFIGURED = 'ℹ️ No polydisperse parameters are configured. Set PD Width > 0 to enable.'
PD_TABLE_COLUMNS = ('**Parameter**', '**PD Width**', '**N Points**', '**Type**', '**Fit Width?**')
PD_WIDTH_LABEL = 'Width'
PD_N_LABEL = 'N'
PD_TYPE_LABEL = 'Type'
PD_VARY_LABEL = 'Fit'
PD_DISTRIBUTION_TYPES = ['gaussian', 'lognormal', 'schulz', 'rectangle', 'boltzmann']
PD_WIDTH_HELP = 'Relative polydispersity width (0.1 = 10%)'
PD_N_HELP = 'Number of quadrature points for integration'
PD_TYPE_HELP = 'Distribution type for polydispersity'
PD_UPDATE_BUTTON = 'Update Polydispersity'
PD_SUCCESS_UPDATED = '✓ Polydispersity settings updated!'
PD_INFO_HEADER = '**About Polydispersity**'
PD_INFO_TEXT = """
Polydispersity accounts for the distribution of sizes in your sample.

- **PD Width**: Relative width of the distribution (e.g., 0.1 = 10% polydispersity)
- **N Points**: Number of integration points (higher = more accurate but slower)
- **Distribution Type**: Shape of the size distribution
  - *Gaussian*: Symmetric bell curve
  - *Lognormal*: Asymmetric, positive values only
  - *Schulz*: Similar to lognormal, common for polymers
  - *Rectangle*: Uniform distribution
"""

# Fitting Section
FIT_ENGINE_LABEL = 'Optimization Engine'
FIT_ENGINE_OPTIONS = ['bumps', 'lmfit']
FIT_ENGINE_HELP = 'Choose the fitting engine'
FIT_METHOD_LABEL = 'Method'
FIT_METHOD_BUMPS = ['amoeba', 'lm', 'newton', 'de']
FIT_METHOD_LMFIT = ['leastsq', 'least_squares', 'differential_evolution']
FIT_METHOD_HELP_BUMPS = 'Optimization method for BUMPS'
FIT_METHOD_HELP_LMFIT = 'Optimization method for LMFit'
FIT_RUN_BUTTON = '🚀 Run Fit'
Q_RANGE_HEADER = '**Fit Q range (Å⁻¹)**'
Q_RANGE_MIN_LABEL = 'Q min'
Q_RANGE_MAX_LABEL = 'Q max'
Q_RANGE_APPLY_BUTTON = 'Apply Q range'
Q_RANGE_RESET_BUTTON = 'Reset Q range'
Q_RANGE_HELP = (
    'Points outside the range stay visible in the plots but are excluded from the fit '
    '(e.g. beam-stop spillover at low Q or background-dominated high Q).'
)
SUCCESS_Q_RANGE_UPDATED = '✓ Fit Q range updated'
SUCCESS_Q_RANGE_RESET = '✓ Fit Q range reset to the full data range'

# Fit Results Section
FIT_RESULTS_HEADER = '📈 Fit Results'
CHI_SQUARED_LABEL = '**Reduced χ² (χ²/dof):** '
FIT_STATS_CAPTION = '{n_points} points, {n_free} free parameters, {dof} degrees of freedom'
FIT_ENGINE_CAPTION = 'Engine: {engine} / {method}'
FIT_CONVERGED_CAPTION = '✓ Optimizer reported convergence'
FIT_NOT_CONVERGED_WARNING = '⚠️ Optimizer did not report convergence: {message}'
FIT_ON_BOUNDS_WARNING = (
    '⚠️ Fitted parameter(s) resting on a bound: {hits}. '
    'Widen the bounds if the boundary was not intentional.'
)
FIT_WARNINGS_HEADER = '**Fit warnings**'
FIT_REPORT_HEADER = '📋 Fit Report'
FITTED_PARAMETERS_HEADER = '**Fitted Parameters**'
ADJUST_PARAMETER_HEADER = '**Adjust Parameter**'
SELECT_PARAMETER_LABEL = 'Select parameter to adjust'
UPDATE_FROM_FIT_BUTTON = 'Update Parameters with Fit Results'
EXPORT_RESULTS_HEADER = '**Export Results**'
SAVE_RESULTS_BUTTON = 'Save Results to CSV'
DOWNLOAD_RESULTS_LABEL = 'Download CSV'
RESULTS_CSV_NAME = 'fit_results.csv'
SAVE_FIT_CURVE_BUTTON = 'Download Fit Curve (CSV)'
FIT_CURVE_CSV_NAME = 'fit_curve.csv'

# Residual Plot Section
RESIDUAL_PLOT_TITLE = 'Normalized Residuals'
RESIDUAL_YAXIS_LABEL = '(I_exp - I_fit) / dI'
RESIDUAL_TRACE_NAME = 'Residuals'
RESIDUAL_ZERO_LINE_NAME = 'Zero'
SHOW_RESIDUALS_LABEL = 'Show residuals plot'
LOG_SCALE_LABEL = 'Log scale'

# Model preview
MODEL_PREVIEW_HEADER = '🔭 Model Preview'
MODEL_PREVIEW_TAB_CURRENT = 'Current parameters'
MODEL_PREVIEW_TAB_COMPARE = 'Compare snapshots'
MODEL_PREVIEW_CAPTION = (
    'The model at the current parameter values, evaluated exactly as a fit would. '
    'Click "Update Parameters" above to redraw it after editing values.'
)
SNAPSHOTS_CAPTION = (
    'Save the current parameter values as a snapshot, change parameters, and '
    'overlay the snapshots to see how each change moves the curve.'
)
SNAPSHOT_LABEL_INPUT = 'Snapshot label'
SNAPSHOT_LABEL_PLACEHOLDER = 'optional, e.g. "radius 40"'
SNAPSHOT_DEFAULT_LABEL = 'Snapshot {n}'
SNAPSHOT_BUTTON = '📌 Snapshot'
CLEAR_SNAPSHOTS_BUTTON = 'Clear'
SNAPSHOTS_RESET_INFO = (
    'Snapshots were cleared: the model, structure factor, parameter links or '
    'polydispersity distribution settings changed, so they can no longer be compared.'
)
NO_SNAPSHOTS_INFO = 'No snapshots yet. Take one to start comparing parameter sets.'

# Parameter correlations
CORRELATIONS_HEADER = '🔗 Parameter Correlations'
CORRELATIONS_CAPTION = (
    'Correlation coefficients ρ between the free parameters, from the fit covariance '
    '(source: {source}). |ρ| near 1 means the data cannot tell the two parameters apart: '
    'consider fixing one, or constraining it with other information.'
)
CORRELATIONS_STRONG_WARNING = '{a} and {b} are strongly correlated (ρ = {rho:+.3f})'

# AI Chat Section
AI_CHAT_SIDEBAR_HEADER = '🤖 AI Assistant'
AI_CHAT_DESCRIPTION = (
    'Ask questions about SANS data analysis, model selection, or parameter interpretation.'
)
AI_CHAT_INPUT_LABEL = 'Your message:'
AI_CHAT_INPUT_PLACEHOLDER = 'Type your question here... (Press Enter for new line)'
AI_CHAT_SEND_BUTTON = '📤 Send'
AI_CHAT_CLEAR_BUTTON = '🗑️ Clear'
AI_CHAT_HISTORY_HEADER = '**Conversation:**'
AI_CHAT_EMPTY_CAPTION = 'No messages yet. Ask a question to get started!'
AI_CHAT_THINKING = 'Thinking...'

# Status Messages
SPINNER_ANALYZING_DATA = 'Analyzing data...'
WARNING_NO_SUGGESTIONS = 'No suggestions found'
WARNING_LOAD_DATA_FIRST = 'Please load data first'

INFO_NO_DATA = '👆 Please upload a SANS data file or load example data from the sidebar.'
WARNING_NO_API_KEY = (
    '⚠️ No API key provided. Please enter your Anthropic API key in the sidebar under '
    "'AI-Assisted' model selection."
)
WARNING_NO_VARY = (
    '⚠️ No parameters are set to vary. Please enable at least one parameter '
    '(or polydispersity width) to fit.'
)
SUCCESS_DATA_UPLOADED = '✓ Data uploaded successfully!'
SUCCESS_EXAMPLE_LOADED = "Example '{name}' loaded with model '{model}'."
SUCCESS_MODEL_LOADED_PREFIX = '✓ Model "'
SUCCESS_MODEL_LOADED_SUFFIX = '" loaded!'
SUCCESS_FIT_COMPLETED = '✓ Fit completed successfully!'
SUCCESS_PARAMS_UPDATED = '✓ Parameters updated!'
SUCCESS_AI_SUGGESTIONS_PREFIX = '✓ Found '
SUCCESS_AI_SUGGESTIONS_SUFFIX = ' suggestions'

# Layout Constants
CHAT_INPUT_HEIGHT = 100
CHAT_HISTORY_HEIGHT = 300
RIGHT_SIDEBAR_TOP = 60
RIGHT_SIDEBAR_WIDTH = 350
RIGHT_SIDEBAR_PADDING_RIGHT = 370
SLIDER_SCALE_MIN = 0.8
SLIDER_SCALE_MAX = 1.2
SLIDER_DEFAULT_MIN = -0.1
SLIDER_DEFAULT_MAX = 0.1
