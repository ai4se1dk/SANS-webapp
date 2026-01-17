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

# Upload Section
UPLOAD_LABEL = 'Upload SANS data file (CSV or .dat)'
UPLOAD_HELP = 'File should contain columns: Q, I(Q), dI(Q)'
EXAMPLE_DATA_BUTTON = 'Load Example Data'
EXAMPLE_DATA_FILE = 'simulated_sans_data.csv'

# Model Selection
SELECTION_METHOD_LABEL = 'Selection Method'
SELECTION_METHOD_OPTIONS = ['Manual', 'AI-Assisted']
SELECTION_METHOD_HELP = 'Choose how to select the fitting model'
MODEL_SELECT_LABEL = 'Select Model'
MODEL_SELECT_HELP = 'Choose a model from the sasmodels library'
AI_ASSISTED_HEADER = '**AI-Assisted Model Suggestion**'
AI_KEY_LABEL = 'OpenAI API Key (optional)'
AI_KEY_HELP = (
    'Enter your OpenAI API key for AI-powered suggestions. '
    'Leave empty for heuristic-based suggestions.'
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
DATA_FORMAT_HELP = """
### Expected Data Format

Your data file should be a CSV or .dat file with three columns:
- **Q**: Scattering vector (Å⁻¹)
- **I(Q)**: Intensity (cm⁻¹)
- **dI(Q)**: Error/uncertainty in intensity

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

# Fit Results Section
FIT_RESULTS_HEADER = '📈 Fit Results'
CHI_SQUARED_LABEL = '**Chi² (χ²):** '
FITTED_PARAMETERS_HEADER = '**Fitted Parameters**'
ADJUST_PARAMETER_HEADER = '**Adjust Parameter**'
SELECT_PARAMETER_LABEL = 'Select parameter to adjust'
UPDATE_FROM_FIT_BUTTON = 'Update Parameters with Fit Results'
EXPORT_RESULTS_HEADER = '**Export Results**'
SAVE_RESULTS_BUTTON = 'Save Results to CSV'
DOWNLOAD_RESULTS_LABEL = 'Download CSV'
RESULTS_CSV_NAME = 'fit_results.csv'

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
ERROR_EXAMPLE_NOT_FOUND = 'Example data file not found!'

INFO_NO_DATA = '👆 Please upload a SANS data file or load example data from the sidebar.'
WARNING_NO_API_KEY = (
    '⚠️ No API key provided. Please enter your OpenAI API key in the sidebar under '
    "'AI-Assisted' model selection."
)
WARNING_NO_VARY = '⚠️ No parameters are set to vary. Please enable at least one parameter to fit.'
SUCCESS_DATA_UPLOADED = '✓ Data uploaded successfully!'
SUCCESS_EXAMPLE_LOADED = '✓ Example data loaded successfully!'
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
