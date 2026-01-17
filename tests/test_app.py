#!/usr/bin/env python
"""
Test script to validate the SANS analysis utilities and Streamlit app functionality.

This test suite covers:
1. Utility functions (sans_analysis_utils.py) - no Streamlit dependency
2. Type definitions (sans_types.py)
3. UI constants (ui_constants.py)
4. Services (services/) - session_state, ai_chat
5. App module imports and functions (app.py) - requires Streamlit
6. SANSFitter integration
"""

import sys
from pathlib import Path

import numpy as np

# Add src directory to path for imports
_src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(_src_path))
sys.path.insert(0, str(_src_path.parent))

# Import utilities first (no Streamlit dependency)
from sans_fitter import SANSFitter  # noqa: E402

import sans_analysis_utils as utils  # noqa: E402

# =============================================================================
# Utility Function Tests (sans_analysis_utils.py)
# =============================================================================


def test_utils_get_all_models():
    """Test model listing from utils module."""
    print('Testing utils.get_all_models()...')
    models = utils.get_all_models()
    assert len(models) > 0, 'No models found!'
    assert 'sphere' in models, 'sphere model not found!'
    assert 'cylinder' in models, 'cylinder model not found!'
    assert 'ellipsoid' in models, 'ellipsoid model not found!'
    print(f'✓ Found {len(models)} models')
    return True


def test_utils_analyze_data():
    """Test data analysis for AI suggestion from utils module."""
    print('\nTesting utils.analyze_data_for_ai_suggestion()...')
    # Create fake data
    q = np.logspace(-3, -1, 50)
    i = 100 * np.exp(-q * 10) + 0.1

    description = utils.analyze_data_for_ai_suggestion(q, i)
    assert len(description) > 0, 'No description generated!'
    assert 'Q range' in description, 'Q range not in description!'
    assert 'Power law slope' in description, 'Power law slope not in description!'
    assert 'Intensity decay' in description, 'Intensity decay not in description!'
    assert 'Data points' in description, 'Data points not in description!'
    print('✓ Data analysis working')
    print(f'  Preview: {description[:100]}...')
    return True


def test_utils_suggest_models_simple():
    """Test simple model suggestion from utils module."""
    print('\nTesting utils.suggest_models_simple()...')

    # Test with steep decay (spherical particles)
    q = np.logspace(-3, -1, 50)
    i_steep = 100 * q ** (-4) + 0.1  # Porod law for spheres
    suggestions_steep = utils.suggest_models_simple(q, i_steep)
    assert len(suggestions_steep) > 0, 'No suggestions generated for steep decay!'
    assert 'sphere' in suggestions_steep, 'sphere not suggested for steep decay!'
    print(f'✓ Steep decay suggestions: {suggestions_steep}')

    # Test with moderate decay (cylindrical)
    i_moderate = 100 * q ** (-2.5) + 0.1
    suggestions_moderate = utils.suggest_models_simple(q, i_moderate)
    assert len(suggestions_moderate) > 0, 'No suggestions generated for moderate decay!'
    print(f'✓ Moderate decay suggestions: {suggestions_moderate}')

    # Test with gentle decay (flat structures)
    i_gentle = 100 * q ** (-1.5) + 0.1
    suggestions_gentle = utils.suggest_models_simple(q, i_gentle)
    assert len(suggestions_gentle) > 0, 'No suggestions generated for gentle decay!'
    print(f'✓ Gentle decay suggestions: {suggestions_gentle}')

    return True


def test_utils_plot_data_and_fit():
    """Test plot generation from utils module."""
    print('\nTesting utils.plot_data_and_fit()...')
    fitter = SANSFitter()

    try:
        fitter.load_data('simulated_sans_data.csv')

        # Test plot without fit
        fig = utils.plot_data_and_fit(fitter, show_fit=False)
        assert fig is not None, 'No figure generated!'
        assert hasattr(fig, 'data'), 'Figure has no data attribute!'
        assert len(fig.data) >= 1, 'Figure should have at least one trace!'
        print('✓ Plot without fit created successfully')

        # Test plot with fit (using dummy fit data)
        fit_q = fitter.data.x
        fit_i = fitter.data.y * 0.9  # Dummy fit
        fig_with_fit = utils.plot_data_and_fit(fitter, show_fit=True, fit_q=fit_q, fit_i=fit_i)
        assert fig_with_fit is not None, 'No figure with fit generated!'
        assert len(fig_with_fit.data) >= 2, 'Figure with fit should have at least two traces!'
        print('✓ Plot with fit created successfully')

        return True
    except Exception as e:
        print(f'✗ Plot creation failed: {e}')
        return False


# =============================================================================
# Type Definitions Tests (sans_types.py)
# =============================================================================


def test_types_module():
    """Test that type definitions are properly defined."""
    print('\nTesting sans_types module...')

    from sans_types import FitParamInfo, FitResult, ParamInfo, ParamUpdate

    # Test ParamInfo structure
    param_info: ParamInfo = {
        'value': 1.0,
        'min': 0.0,
        'max': 10.0,
        'vary': True,
        'description': 'Test parameter',
    }
    assert param_info['value'] == 1.0, 'ParamInfo value incorrect!'
    assert param_info['vary'] is True, 'ParamInfo vary incorrect!'
    print('✓ ParamInfo TypedDict works correctly')

    # Test FitParamInfo structure
    fit_param_info: FitParamInfo = {
        'value': 2.5,
        'stderr': 0.1,
    }
    assert fit_param_info['value'] == 2.5, 'FitParamInfo value incorrect!'
    print('✓ FitParamInfo TypedDict works correctly')

    # Test FitResult structure
    fit_result: FitResult = {
        'chisq': 1.5,
        'parameters': {'scale': fit_param_info},
    }
    assert fit_result['chisq'] == 1.5, 'FitResult chisq incorrect!'
    print('✓ FitResult TypedDict works correctly')

    # Test ParamUpdate structure
    param_update: ParamUpdate = {
        'value': 5.0,
        'min': 0.0,
        'max': 100.0,
        'vary': False,
    }
    assert param_update['value'] == 5.0, 'ParamUpdate value incorrect!'
    print('✓ ParamUpdate TypedDict works correctly')

    return True


# =============================================================================
# UI Constants Tests (ui_constants.py)
# =============================================================================


def test_ui_constants():
    """Test that UI constants are properly defined."""
    print('\nTesting ui_constants module...')

    import ui_constants

    # Test app configuration constants
    assert hasattr(ui_constants, 'APP_PAGE_TITLE'), 'APP_PAGE_TITLE not found!'
    assert hasattr(ui_constants, 'APP_TITLE'), 'APP_TITLE not found!'
    assert ui_constants.APP_PAGE_TITLE == 'SANS Data Analysis', 'APP_PAGE_TITLE incorrect!'
    print('✓ App configuration constants present')

    # Test sidebar constants
    assert hasattr(ui_constants, 'SIDEBAR_CONTROLS_HEADER'), 'SIDEBAR_CONTROLS_HEADER not found!'
    assert hasattr(ui_constants, 'SIDEBAR_DATA_UPLOAD_HEADER'), (
        'SIDEBAR_DATA_UPLOAD_HEADER not found!'
    )
    print('✓ Sidebar constants present')

    # Test parameter constants
    assert hasattr(ui_constants, 'PARAMETER_COLUMNS_LABELS'), 'PARAMETER_COLUMNS_LABELS not found!'
    assert len(ui_constants.PARAMETER_COLUMNS_LABELS) == 5, 'Should have 5 column labels!'
    print('✓ Parameter constants present')

    # Test fit constants
    assert hasattr(ui_constants, 'FIT_ENGINE_OPTIONS'), 'FIT_ENGINE_OPTIONS not found!'
    assert 'bumps' in ui_constants.FIT_ENGINE_OPTIONS, 'bumps not in FIT_ENGINE_OPTIONS!'
    assert 'lmfit' in ui_constants.FIT_ENGINE_OPTIONS, 'lmfit not in FIT_ENGINE_OPTIONS!'
    print('✓ Fit engine constants present')

    # Test display limits
    assert hasattr(ui_constants, 'MAX_FLOAT_DISPLAY'), 'MAX_FLOAT_DISPLAY not found!'
    assert hasattr(ui_constants, 'MIN_FLOAT_DISPLAY'), 'MIN_FLOAT_DISPLAY not found!'
    assert ui_constants.MAX_FLOAT_DISPLAY == 1e300, 'MAX_FLOAT_DISPLAY incorrect!'
    print('✓ Display limit constants present')

    return True


# =============================================================================
# Services Tests (services/)
# =============================================================================


def test_session_state_clamp_for_display():
    """Test the clamp_for_display function from session_state service."""
    print('\nTesting services.session_state.clamp_for_display()...')

    from services.session_state import clamp_for_display

    # Test normal values
    assert clamp_for_display(1.0) == 1.0, 'Normal value should be unchanged!'
    assert clamp_for_display(-5.0) == -5.0, 'Negative value should be unchanged!'
    assert clamp_for_display(0.0) == 0.0, 'Zero should be unchanged!'
    print('✓ Normal values pass through unchanged')

    # Test infinity values
    clamped_inf = clamp_for_display(float('inf'))
    assert clamped_inf < float('inf'), 'Positive infinity should be clamped!'
    assert clamped_inf == 1e300, 'Positive infinity should clamp to MAX_FLOAT_DISPLAY!'
    print('✓ Positive infinity clamped correctly')

    clamped_neg_inf = clamp_for_display(float('-inf'))
    assert clamped_neg_inf > float('-inf'), 'Negative infinity should be clamped!'
    assert clamped_neg_inf == -1e300, 'Negative infinity should clamp to MIN_FLOAT_DISPLAY!'
    print('✓ Negative infinity clamped correctly')

    return True


def test_session_state_helper_functions():
    """Test session state helper functions with mocked Streamlit session state."""
    print('\nTesting services.session_state helper functions...')

    from unittest.mock import MagicMock, patch

    from sans_fitter import SANSFitter

    from services import session_state

    # Create a real SANSFitter instance for the mock
    test_fitter = SANSFitter()

    # Create a mock session state dictionary
    mock_session_state = {
        'fitter': test_fitter,
        'data_loaded': True,
        'model_selected': True,
        'fit_completed': False,
        'chat_api_key': 'test-api-key',
        'value_scale': 1.0,
        'min_scale': 0.0,
        'max_scale': 10.0,
        'vary_scale': True,
    }

    # Create a proper mock that behaves like st.session_state (supports both dict and attr access)
    class MockSessionState:
        def __getitem__(self, key):
            return mock_session_state[key]

        def __getattr__(self, key):
            return mock_session_state[key]

        def __contains__(self, key):
            return key in mock_session_state

        def keys(self):
            return mock_session_state.keys()

    # Patch st.session_state
    with patch.object(session_state, 'st') as mock_st:
        mock_st.session_state = MockSessionState()

        # Test get_fitter
        fitter = session_state.get_fitter()
        assert fitter is test_fitter, 'get_fitter should return the test SANSFitter instance!'
        print('✓ get_fitter() works correctly')

        # Test is_data_loaded
        assert session_state.is_data_loaded() is True, 'is_data_loaded should return True!'
        print('✓ is_data_loaded() works correctly')

        # Test is_model_selected
        assert session_state.is_model_selected() is True, 'is_model_selected should return True!'
        print('✓ is_model_selected() works correctly')

        # Test is_fit_completed
        assert session_state.is_fit_completed() is False, 'is_fit_completed should return False!'
        print('✓ is_fit_completed() works correctly')

        # Test get_api_key
        api_key = session_state.get_api_key()
        assert api_key == 'test-api-key', 'get_api_key should return test-api-key!'
        print('✓ get_api_key() works correctly')

    return True


def test_session_state_clear_parameter_state():
    """Test clear_parameter_state function."""
    print('\nTesting services.session_state.clear_parameter_state()...')

    from unittest.mock import MagicMock, patch

    from services import session_state

    # Create a mock session state with parameter keys
    mock_session_state = {
        'fitter': MagicMock(),
        'data_loaded': True,
        'value_scale': 1.0,
        'min_scale': 0.0,
        'max_scale': 10.0,
        'vary_scale': True,
        'value_radius': 50.0,
        'min_radius': 1.0,
        'max_radius': 1000.0,
        'vary_radius': True,
    }

    deleted_keys = []

    class MockSessionState:
        def keys(self):
            return list(mock_session_state.keys())

        def __delitem__(self, key):
            deleted_keys.append(key)
            del mock_session_state[key]

    with patch.object(session_state, 'st') as mock_st:
        mock_st.session_state = MockSessionState()

        session_state.clear_parameter_state()

        # Verify parameter keys were deleted
        assert 'value_scale' in deleted_keys, 'value_scale should be deleted!'
        assert 'min_scale' in deleted_keys, 'min_scale should be deleted!'
        assert 'vary_radius' in deleted_keys, 'vary_radius should be deleted!'
        assert 'fitter' not in deleted_keys, 'fitter should NOT be deleted!'
        assert 'data_loaded' not in deleted_keys, 'data_loaded should NOT be deleted!'
        print(f'✓ Deleted {len(deleted_keys)} parameter keys correctly')

    return True


def test_session_state_init():
    """Test init_session_state function."""
    print('\nTesting services.session_state.init_session_state()...')

    from unittest.mock import MagicMock, patch

    from services import session_state

    # Create empty session state
    mock_session_state = {}

    with patch.object(session_state, 'st') as mock_st:
        mock_st.session_state = MagicMock()
        mock_st.session_state.__contains__ = lambda self, key: key in mock_session_state
        mock_st.session_state.__setitem__ = lambda self, key, val: mock_session_state.__setitem__(
            key, val
        )

        session_state.init_session_state()

        # Check defaults were set
        assert 'data_loaded' in mock_session_state, 'data_loaded should be initialized!'
        assert 'model_selected' in mock_session_state, 'model_selected should be initialized!'
        assert 'fit_completed' in mock_session_state, 'fit_completed should be initialized!'
        assert 'fitter' in mock_session_state, 'fitter should be initialized!'
        assert mock_session_state['data_loaded'] is False, 'data_loaded should default to False!'
        print('✓ init_session_state() initializes all required keys')

    return True


def test_ai_chat_service():
    """Test the ai_chat service module structure."""
    print('\nTesting services.ai_chat module...')

    from services import ai_chat

    # Check that functions exist
    assert hasattr(ai_chat, 'send_chat_message'), 'send_chat_message not found!'
    assert hasattr(ai_chat, 'suggest_models_ai'), 'suggest_models_ai not found!'
    print('✓ AI chat functions available')

    # Test suggest_models_ai without API key (should fall back to simple)
    q = np.logspace(-3, -1, 50)
    i = 100 * q ** (-4) + 0.1

    # This should return simple suggestions when no API key is provided
    suggestions = ai_chat.suggest_models_ai(q, i, api_key=None)
    assert isinstance(suggestions, list), 'suggest_models_ai should return a list!'
    assert len(suggestions) > 0, 'Should have at least one suggestion!'
    print(f'✓ Fallback suggestions work: {suggestions}')

    return True


def test_ai_chat_send_message_no_api_key():
    """Test send_chat_message without API key."""
    print('\nTesting services.ai_chat.send_chat_message() without API key...')

    from services.ai_chat import send_chat_message

    fitter = SANSFitter()

    # Test without API key
    response = send_chat_message('What is SANS?', api_key=None, fitter=fitter)
    assert 'API key' in response, 'Should warn about missing API key!'
    print('✓ send_chat_message returns warning when no API key')

    return True


def test_ai_chat_send_message_with_mock():
    """Test send_chat_message with mocked OpenAI API."""
    print('\nTesting services.ai_chat.send_chat_message() with mock...')

    from unittest.mock import MagicMock, patch

    from services import ai_chat

    fitter = SANSFitter()
    fitter.load_data('simulated_sans_data.csv')
    fitter.set_model('sphere')

    # Create mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = 'This is a test response about SANS analysis.'

    # Mock session state
    mock_session_state = {
        'current_model': 'sphere',
        'model_selected': True,
        'fit_completed': False,
    }

    with patch.object(ai_chat, 'st') as mock_st:
        mock_st.session_state = MagicMock()
        mock_st.session_state.__getitem__ = lambda self, key: mock_session_state.get(key)
        mock_st.session_state.__contains__ = lambda self, key: key in mock_session_state

        with patch('services.ai_chat.create_chat_completion', return_value=mock_response):
            response = ai_chat.send_chat_message('What is SANS?', api_key='test-key', fitter=fitter)

            assert response == 'This is a test response about SANS analysis.', (
                'Response should match mock!'
            )
            print('✓ send_chat_message works with mocked OpenAI API')

    return True


def test_ai_chat_send_message_error_handling():
    """Test send_chat_message error handling."""
    print('\nTesting services.ai_chat.send_chat_message() error handling...')

    from unittest.mock import MagicMock, patch

    from services import ai_chat

    fitter = SANSFitter()

    # Mock session state
    mock_session_state = {}

    with patch.object(ai_chat, 'st') as mock_st:
        mock_st.session_state = MagicMock()
        mock_st.session_state.__getitem__ = lambda self, key: mock_session_state.get(key)
        mock_st.session_state.__contains__ = lambda self, key: key in mock_session_state

        with patch('services.ai_chat.create_chat_completion', side_effect=Exception('API Error')):
            response = ai_chat.send_chat_message('What is SANS?', api_key='test-key', fitter=fitter)

            assert 'Error' in response, 'Response should contain error message!'
            assert 'API Error' in response, 'Response should contain error details!'
            print('✓ send_chat_message handles errors gracefully')

    return True


# =============================================================================
# SANSFitter Integration Tests
# =============================================================================


def test_fitter_integration():
    """Test SANSFitter integration."""
    print('\nTesting SANSFitter integration...')
    fitter = SANSFitter()

    # Load example data
    try:
        fitter.load_data('simulated_sans_data.csv')
        assert fitter.data is not None, 'Data not loaded!'
        assert len(fitter.data.x) > 0, 'No data points!'
        print('✓ Data loaded successfully')
    except Exception as e:
        print(f'✗ Data loading failed: {e}')
        return False

    # Set model
    try:
        fitter.set_model('sphere')
        print('✓ Model loaded successfully')
    except Exception as e:
        print(f'✗ Model loading failed: {e}')
        return False

    # Check parameters
    assert len(fitter.params) > 0, 'No parameters loaded!'
    assert 'radius' in fitter.params, 'radius parameter not found!'
    assert 'scale' in fitter.params, 'scale parameter not found!'
    print(f'✓ Found {len(fitter.params)} parameters: {list(fitter.params.keys())}')

    return True


# =============================================================================
# App Module Tests (requires Streamlit)
# =============================================================================


def test_app_imports():
    """Test that app module can be imported and has expected functions."""
    print('\nTesting app module imports...')

    try:
        import app

        # Check that app re-exports the utility functions (backwards compatibility)
        assert hasattr(app, 'get_all_models'), 'get_all_models not available in app!'
        assert hasattr(app, 'analyze_data_for_ai_suggestion'), (
            'analyze_data_for_ai_suggestion not available in app!'
        )
        assert hasattr(app, 'suggest_models_simple'), 'suggest_models_simple not available in app!'
        assert hasattr(app, 'plot_data_and_fit'), 'plot_data_and_fit not available in app!'
        print('✓ Utility functions re-exported from app (backwards compatible)')

        # Check app-specific functions
        assert hasattr(app, 'suggest_models_ai'), 'suggest_models_ai not found in app!'
        assert hasattr(app, 'main'), 'main function not found in app!'
        assert hasattr(app, 'clamp_for_display'), 'clamp_for_display not found in app!'
        print('✓ App-specific functions available')

        # Check refactored module imports
        assert hasattr(app, 'render_data_preview'), 'render_data_preview not imported!'
        assert hasattr(app, 'render_fit_results'), 'render_fit_results not imported!'
        assert hasattr(app, 'render_parameter_configuration'), (
            'render_parameter_configuration not imported!'
        )
        print('✓ Refactored component functions imported')

        return True
    except ImportError as e:
        print(f'✗ App import failed: {e}')
        return False


def test_app_clamp_for_display():
    """Test the clamp_for_display function in app module."""
    print('\nTesting app.clamp_for_display()...')

    try:
        import app

        # Test normal values
        assert app.clamp_for_display(1.0) == 1.0, 'Normal value should be unchanged!'
        assert app.clamp_for_display(-5.0) == -5.0, 'Negative value should be unchanged!'

        # Test infinity values
        clamped_inf = app.clamp_for_display(float('inf'))
        assert clamped_inf < float('inf'), 'Positive infinity should be clamped!'

        clamped_neg_inf = app.clamp_for_display(float('-inf'))
        assert clamped_neg_inf > float('-inf'), 'Negative infinity should be clamped!'

        print('✓ clamp_for_display working correctly')
        return True
    except Exception as e:
        print(f'✗ clamp_for_display test failed: {e}')
        return False


# =============================================================================
# Components Tests (components/)
# =============================================================================


def test_components_imports():
    """Test that component modules can be imported."""
    print('\nTesting components module imports...')

    try:
        from components import (
            apply_fit_results_to_params,
            apply_param_updates,
            apply_pending_preset,
            build_param_updates_from_params,
            render_ai_chat_sidebar,
            render_data_preview,
            render_data_upload_sidebar,
            render_fit_results,
            render_model_selection_sidebar,
            render_parameter_configuration,
            render_parameter_table,
        )

        print('✓ All component functions importable from components package')

        # Test individual module imports
        from components import data_preview, fit_results, parameters, sidebar

        assert hasattr(data_preview, 'render_data_preview'), (
            'render_data_preview not in data_preview!'
        )
        assert hasattr(fit_results, 'render_fit_results'), 'render_fit_results not in fit_results!'
        assert hasattr(parameters, 'render_parameter_table'), (
            'render_parameter_table not in parameters!'
        )
        assert hasattr(sidebar, 'render_data_upload_sidebar'), (
            'render_data_upload_sidebar not in sidebar!'
        )
        print('✓ Individual component modules have expected functions')

        return True
    except ImportError as e:
        print(f'✗ Components import failed: {e}')
        return False


def test_services_imports():
    """Test that service modules can be imported."""
    print('\nTesting services module imports...')

    try:
        from services import (
            clamp_for_display,
            init_session_state,
            send_chat_message,
            suggest_models_ai,
        )

        print('✓ All service functions importable from services package')

        # Test individual module imports
        from services import ai_chat, session_state

        assert hasattr(session_state, 'init_session_state'), (
            'init_session_state not in session_state!'
        )
        assert hasattr(session_state, 'clamp_for_display'), (
            'clamp_for_display not in session_state!'
        )
        assert hasattr(ai_chat, 'send_chat_message'), 'send_chat_message not in ai_chat!'
        assert hasattr(ai_chat, 'suggest_models_ai'), 'suggest_models_ai not in ai_chat!'
        print('✓ Individual service modules have expected functions')

        return True
    except ImportError as e:
        print(f'✗ Services import failed: {e}')
        return False


def test_parameters_build_updates():
    """Test the build_param_updates_from_params function."""
    print('\nTesting components.parameters.build_param_updates_from_params()...')

    from components.parameters import build_param_updates_from_params  # noqa: F402
    from sans_types import ParamInfo  # noqa: F402

    # Create test params
    test_params: dict[str, ParamInfo] = {
        'scale': {'value': 1.0, 'min': 0.0, 'max': 10.0, 'vary': True, 'description': 'Scale'},
        'radius': {'value': 50.0, 'min': 1.0, 'max': 1000.0, 'vary': True, 'description': 'Radius'},
    }

    updates = build_param_updates_from_params(test_params)

    assert 'scale' in updates, 'scale not in updates!'
    assert 'radius' in updates, 'radius not in updates!'
    assert updates['scale']['value'] == 1.0, 'scale value incorrect!'
    assert updates['scale']['vary'] is True, 'scale vary incorrect!'
    assert updates['radius']['min'] == 1.0, 'radius min incorrect!'
    print('✓ build_param_updates_from_params works correctly')

    return True


def test_parameters_apply_param_updates():
    """Test the apply_param_updates function."""
    print('\nTesting components.parameters.apply_param_updates()...')

    from components.parameters import apply_param_updates
    from sans_types import ParamUpdate

    fitter = SANSFitter()
    fitter.set_model('sphere')

    # Get original values
    fitter.params['scale']['value']
    fitter.params['radius']['value']

    # Create param updates
    param_updates: dict[str, ParamUpdate] = {
        'scale': {'value': 0.5, 'min': 0.0, 'max': 5.0, 'vary': True},
        'radius': {'value': 75.0, 'min': 10.0, 'max': 200.0, 'vary': False},
    }

    apply_param_updates(fitter, param_updates)

    # Verify updates were applied
    assert fitter.params['scale']['value'] == 0.5, 'scale value not updated!'
    assert fitter.params['scale']['max'] == 5.0, 'scale max not updated!'
    assert fitter.params['radius']['value'] == 75.0, 'radius value not updated!'
    assert fitter.params['radius']['vary'] is False, 'radius vary not updated!'
    print('✓ apply_param_updates works correctly')

    return True


def test_parameters_apply_pending_preset():
    """Test the apply_pending_preset function."""
    print('\nTesting components.parameters.apply_pending_preset()...')

    from unittest.mock import MagicMock, patch

    from components import parameters
    from sans_types import ParamInfo

    fitter = SANSFitter()
    fitter.set_model('sphere')

    params: dict[str, ParamInfo] = {
        'scale': {'value': 1.0, 'min': 0.0, 'max': 10.0, 'vary': False, 'description': 'Scale'},
        'background': {
            'value': 0.001,
            'min': 0.0,
            'max': 1.0,
            'vary': False,
            'description': 'Background',
        },
        'radius': {
            'value': 50.0,
            'min': 1.0,
            'max': 1000.0,
            'vary': False,
            'description': 'Radius',
        },
    }

    # Test scale_background preset
    mock_session_state = {'pending_preset': 'scale_background'}

    class MockSessionState:
        def __contains__(self, key):
            return key in mock_session_state

        def __getitem__(self, key):
            return mock_session_state[key]

        def __getattr__(self, key):
            return mock_session_state[key]

        def __setitem__(self, key, value):
            mock_session_state[key] = value

        def __delitem__(self, key):
            del mock_session_state[key]

        def __delattr__(self, key):
            del mock_session_state[key]

    with patch.object(parameters, 'st') as mock_st:
        mock_st.session_state = MockSessionState()

        parameters.apply_pending_preset(fitter, params)

        # Verify preset was applied
        assert fitter.params['scale']['vary'] is True, 'scale should be set to vary!'
        assert fitter.params['background']['vary'] is True, 'background should be set to vary!'
        assert fitter.params['radius']['vary'] is False, 'radius should NOT be set to vary!'
        assert 'pending_preset' not in mock_session_state, 'pending_preset should be deleted!'
        print('✓ apply_pending_preset (scale_background) works correctly')

    # Test fit_all preset
    mock_session_state = {'pending_preset': 'fit_all'}

    with patch.object(parameters, 'st') as mock_st:
        mock_st.session_state = MockSessionState()

        parameters.apply_pending_preset(fitter, params)

        assert fitter.params['scale']['vary'] is True, 'scale should be set to vary!'
        assert fitter.params['radius']['vary'] is True, 'radius should be set to vary!'
        print('✓ apply_pending_preset (fit_all) works correctly')

    # Test fix_all preset
    mock_session_state = {'pending_preset': 'fix_all'}

    with patch.object(parameters, 'st') as mock_st:
        mock_st.session_state = MockSessionState()

        parameters.apply_pending_preset(fitter, params)

        assert fitter.params['scale']['vary'] is False, 'scale should NOT be set to vary!'
        assert fitter.params['radius']['vary'] is False, 'radius should NOT be set to vary!'
        print('✓ apply_pending_preset (fix_all) works correctly')

    return True


def test_parameters_apply_fit_results():
    """Test the apply_fit_results_to_params function."""
    print('\nTesting components.parameters.apply_fit_results_to_params()...')

    from unittest.mock import patch

    from components import parameters
    from sans_types import ParamInfo

    fitter = SANSFitter()
    fitter.set_model('sphere')

    params: dict[str, ParamInfo] = {
        'scale': {'value': 1.0, 'min': 0.0, 'max': 10.0, 'vary': True, 'description': 'Scale'},
        'radius': {'value': 50.0, 'min': 1.0, 'max': 1000.0, 'vary': True, 'description': 'Radius'},
    }

    # Mock session state with fit result
    mock_session_state = {
        'pending_update_from_fit': True,
        'fit_result': {
            'chisq': 1.5,
            'parameters': {
                'scale': {'value': 0.85, 'stderr': 0.02},
                'radius': {'value': 62.3, 'stderr': 1.5},
            },
        },
    }

    class MockSessionState:
        def __contains__(self, key):
            return key in mock_session_state

        def __getitem__(self, key):
            return mock_session_state[key]

        def __getattr__(self, key):
            return mock_session_state[key]

        def __setitem__(self, key, value):
            mock_session_state[key] = value

        def __delitem__(self, key):
            del mock_session_state[key]

        def __delattr__(self, key):
            del mock_session_state[key]

    with patch.object(parameters, 'st') as mock_st:
        mock_st.session_state = MockSessionState()

        parameters.apply_fit_results_to_params(fitter, params)

        # Verify fit results were applied
        assert fitter.params['scale']['value'] == 0.85, 'scale value not updated from fit!'
        assert fitter.params['radius']['value'] == 62.3, 'radius value not updated from fit!'
        assert 'pending_update_from_fit' not in mock_session_state, (
            'pending_update_from_fit should be deleted!'
        )
        assert mock_session_state.get('value_scale') == 0.85, (
            'value_scale in session state not updated!'
        )
        print('✓ apply_fit_results_to_params works correctly')

    return True


def test_parameters_apply_fit_results_no_pending():
    """Test apply_fit_results_to_params does nothing without pending flag."""
    print('\nTesting components.parameters.apply_fit_results_to_params() without pending...')

    from unittest.mock import patch

    from components import parameters
    from sans_types import ParamInfo

    fitter = SANSFitter()
    fitter.set_model('sphere')
    original_scale = fitter.params['scale']['value']

    params: dict[str, ParamInfo] = {
        'scale': {'value': 1.0, 'min': 0.0, 'max': 10.0, 'vary': True, 'description': 'Scale'},
    }

    # Mock session state WITHOUT pending_update_from_fit
    mock_session_state = {
        'fit_result': {
            'chisq': 1.5,
            'parameters': {'scale': {'value': 0.85, 'stderr': 0.02}},
        },
    }

    class MockSessionState:
        def __contains__(self, key):
            return key in mock_session_state

    with patch.object(parameters, 'st') as mock_st:
        mock_st.session_state = MockSessionState()

        parameters.apply_fit_results_to_params(fitter, params)

        # Verify nothing changed
        assert fitter.params['scale']['value'] == original_scale, (
            'scale should NOT be updated without pending flag!'
        )
        print('✓ apply_fit_results_to_params correctly ignores without pending flag')

    return True


# =============================================================================
# OpenAI Client Tests (openai_client.py)
# =============================================================================


def test_openai_client_import():
    """Test that openai_client module can be imported."""
    print('\nTesting openai_client module import...')

    from openai_client import create_chat_completion

    assert callable(create_chat_completion), 'create_chat_completion should be callable!'
    print('✓ openai_client.create_chat_completion is available')

    return True


def test_openai_client_create_chat_completion():
    """Test create_chat_completion with mocked OpenAI client."""
    print('\nTesting openai_client.create_chat_completion() with mock...')

    from unittest.mock import MagicMock, patch

    # Create mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = 'Test response'

    # Mock the OpenAI client
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response

    # Patch 'openai.OpenAI' since it's imported inside the function
    with patch('openai.OpenAI', return_value=mock_client_instance) as mock_openai:
        import openai_client

        response = openai_client.create_chat_completion(
            api_key='test-api-key',
            model='gpt-4o',
            messages=[{'role': 'user', 'content': 'Hello'}],
            max_tokens=100,
        )

        # Verify OpenAI was called with correct API key
        mock_openai.assert_called_once_with(api_key='test-api-key')

        # Verify chat.completions.create was called with correct parameters
        mock_client_instance.chat.completions.create.assert_called_once()
        call_kwargs = mock_client_instance.chat.completions.create.call_args
        assert call_kwargs.kwargs['model'] == 'gpt-4o', 'Model should be gpt-4o!'
        assert call_kwargs.kwargs['max_tokens'] == 100, 'max_tokens should be 100!'

        # Verify response
        assert response == mock_response, 'Should return the mock response!'
        print('✓ create_chat_completion calls OpenAI correctly')

    return True


def test_openai_client_messages_conversion():
    """Test that messages iterable is converted to list."""
    print('\nTesting openai_client.create_chat_completion() messages conversion...')

    from unittest.mock import MagicMock, patch

    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = MagicMock()

    # Pass messages as a generator (iterable)
    def message_generator():
        yield {'role': 'system', 'content': 'You are helpful'}
        yield {'role': 'user', 'content': 'Hello'}

    with patch('openai.OpenAI', return_value=mock_client_instance):
        import openai_client

        openai_client.create_chat_completion(
            api_key='test-key',
            model='gpt-4o',
            messages=message_generator(),
            max_tokens=50,
        )

        # Verify messages were converted to list
        call_kwargs = mock_client_instance.chat.completions.create.call_args
        messages_arg = call_kwargs.kwargs['messages']
        assert isinstance(messages_arg, list), 'Messages should be converted to list!'
        assert len(messages_arg) == 2, 'Should have 2 messages!'
        print('✓ create_chat_completion converts iterable to list')

    return True


# =============================================================================
# Fit Results Component Tests (components/fit_results.py)
# =============================================================================


def test_fit_results_imports():
    """Test that fit_results module can be imported."""
    print('\nTesting components.fit_results module imports...')

    from components.fit_results import (
        _render_export_section,
        _render_fit_statistics,
        _render_fitted_parameters_table,
        _render_parameter_slider,
        render_fit_results,
    )

    assert callable(render_fit_results), 'render_fit_results should be callable!'
    assert callable(_render_fit_statistics), '_render_fit_statistics should be callable!'
    assert callable(_render_fitted_parameters_table), (
        '_render_fitted_parameters_table should be callable!'
    )
    assert callable(_render_parameter_slider), '_render_parameter_slider should be callable!'
    assert callable(_render_export_section), '_render_export_section should be callable!'
    print('✓ All fit_results functions are importable')

    return True


def test_fit_results_build_fitted_params_list():
    """Test building fitted parameters list logic (extracted from _render_fitted_parameters_table)."""
    print('\nTesting fit_results fitted params list building...')

    # Test the logic for building fitted params from fit_result
    fit_result = {
        'chisq': 1.5,
        'parameters': {
            'scale': {'value': 0.85, 'stderr': 0.02},
            'radius': {'value': 62.3, 'stderr': 1.5},
            'background': {'value': 0.001, 'stderr': 0.0001},
        },
    }

    fitter_params = {
        'scale': {'value': 0.85, 'vary': True},
        'radius': {'value': 62.3, 'vary': True},
        'background': {'value': 0.001, 'vary': False},  # Not fitted
        'sld': {'value': 1.0, 'vary': False},
    }

    fitted_params = []
    for name, param_info in fit_result['parameters'].items():
        if name in fitter_params and fitter_params[name]['vary']:
            value = param_info.get('value')
            stderr = param_info.get('stderr')
            if value is None:
                continue
            if isinstance(stderr, (int, float)):
                error_text = f'{stderr:.4g}'
            elif stderr is None:
                error_text = 'N/A'
            else:
                error_text = f'{stderr}'
            fitted_params.append(
                {
                    'Parameter': name,
                    'Value': f'{value:.4g}',
                    'Error': error_text,
                }
            )

    assert len(fitted_params) == 2, 'Should have 2 fitted parameters!'
    param_names = [p['Parameter'] for p in fitted_params]
    assert 'scale' in param_names, 'scale should be in fitted params!'
    assert 'radius' in param_names, 'radius should be in fitted params!'
    assert 'background' not in param_names, 'background should NOT be in fitted params (not vary)!'
    print('✓ Fitted params list building logic works correctly')

    return True


def test_fit_results_slider_range_calculation():
    """Test slider range calculation logic from _render_parameter_slider."""
    print('\nTesting fit_results slider range calculation...')

    from ui_constants import (
        SLIDER_DEFAULT_MAX,
        SLIDER_DEFAULT_MIN,
        SLIDER_SCALE_MAX,
        SLIDER_SCALE_MIN,
    )

    # Test non-zero value
    current_value = 50.0
    slider_min = current_value * SLIDER_SCALE_MIN
    slider_max = current_value * SLIDER_SCALE_MAX

    assert slider_min == 50.0 * 0.8, 'slider_min should be 80% of value!'
    assert slider_max == 50.0 * 1.2, 'slider_max should be 120% of value!'
    print(f'✓ Non-zero value range: [{slider_min}, {slider_max}]')

    # Test zero value
    current_value = 0.0
    if current_value != 0:
        slider_min = current_value * SLIDER_SCALE_MIN
        slider_max = current_value * SLIDER_SCALE_MAX
    else:
        slider_min = SLIDER_DEFAULT_MIN
        slider_max = SLIDER_DEFAULT_MAX

    assert slider_min == SLIDER_DEFAULT_MIN, 'slider_min should use default for zero!'
    assert slider_max == SLIDER_DEFAULT_MAX, 'slider_max should use default for zero!'
    print(f'✓ Zero value range: [{slider_min}, {slider_max}]')

    return True


def test_fit_results_export_data_structure():
    """Test export data structure from _render_export_section."""
    print('\nTesting fit_results export data structure...')

    import pandas as pd

    # Simulate fitter.params
    fitter_params = {
        'scale': {'value': 0.85, 'min': 0.0, 'max': 10.0, 'vary': True},
        'radius': {'value': 62.3, 'min': 1.0, 'max': 200.0, 'vary': True},
        'background': {'value': 0.001, 'min': 0.0, 'max': 1.0, 'vary': False},
    }

    results_data = []
    for name, info in fitter_params.items():
        results_data.append(
            {
                'Parameter': name,
                'Value': info['value'],
                'Min': info['min'],
                'Max': info['max'],
                'Fitted': info['vary'],
            }
        )

    df_results = pd.DataFrame(results_data)
    csv = df_results.to_csv(index=False)

    assert len(results_data) == 3, 'Should have 3 parameters in export!'
    assert 'Parameter,Value,Min,Max,Fitted' in csv, 'CSV should have correct headers!'
    assert 'scale,0.85,0.0,10.0,True' in csv, 'CSV should contain scale data!'
    print('✓ Export data structure is correct')

    return True


# =============================================================================
# Data Preview Component Tests (components/data_preview.py)
# =============================================================================


def test_data_preview_imports():
    """Test that data_preview module can be imported."""
    print('\nTesting components.data_preview module imports...')

    from components.data_preview import render_data_preview

    assert callable(render_data_preview), 'render_data_preview should be callable!'
    print('✓ data_preview functions are importable')

    return True


# =============================================================================
# Sidebar Component Tests (components/sidebar.py)
# =============================================================================


def test_sidebar_imports():
    """Test that sidebar module can be imported."""
    print('\nTesting components.sidebar module imports...')

    from components.sidebar import (
        render_ai_chat_sidebar,
        render_data_upload_sidebar,
        render_model_selection_sidebar,
    )

    assert callable(render_data_upload_sidebar), 'render_data_upload_sidebar should be callable!'
    assert callable(render_model_selection_sidebar), (
        'render_model_selection_sidebar should be callable!'
    )
    assert callable(render_ai_chat_sidebar), 'render_ai_chat_sidebar should be callable!'
    print('✓ All sidebar functions are importable')

    return True


# =============================================================================
# Main Test Runner
# =============================================================================

if __name__ == '__main__':
    print('=' * 70)
    print('SANS Analysis - Test Suite (Refactored)')
    print('=' * 70)
    print('\nThis test covers the refactored module structure:')
    print('  - sans_analysis_utils.py (utility functions)')
    print('  - sans_types.py (type definitions)')
    print('  - ui_constants.py (UI string constants)')
    print('  - services/ (session_state, ai_chat)')
    print('  - components/ (sidebar, parameters, data_preview, fit_results)')
    print('  - app.py (main orchestration)')

    results = {}

    # Run utility tests (no Streamlit dependency)
    print('\n' + '-' * 70)
    print('UTILITY FUNCTION TESTS (sans_analysis_utils.py)')
    print('-' * 70)

    try:
        results['utils_get_all_models'] = test_utils_get_all_models()
        results['utils_analyze_data'] = test_utils_analyze_data()
        results['utils_suggest_models'] = test_utils_suggest_models_simple()
        results['utils_plot'] = test_utils_plot_data_and_fit()
    except Exception as e:
        print(f'\n✗ Utility tests failed with exception: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Run type definitions tests
    print('\n' + '-' * 70)
    print('TYPE DEFINITIONS TESTS (sans_types.py)')
    print('-' * 70)

    try:
        results['types_module'] = test_types_module()
    except Exception as e:
        print(f'\n✗ Types tests failed with exception: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Run UI constants tests
    print('\n' + '-' * 70)
    print('UI CONSTANTS TESTS (ui_constants.py)')
    print('-' * 70)

    try:
        results['ui_constants'] = test_ui_constants()
    except Exception as e:
        print(f'\n✗ UI constants tests failed with exception: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Run services tests
    print('\n' + '-' * 70)
    print('SERVICES TESTS (services/)')
    print('-' * 70)

    try:
        results['session_state_clamp'] = test_session_state_clamp_for_display()
        results['session_state_helpers'] = test_session_state_helper_functions()
        results['session_state_clear'] = test_session_state_clear_parameter_state()
        results['session_state_init'] = test_session_state_init()
        results['ai_chat_service'] = test_ai_chat_service()
        results['ai_chat_no_key'] = test_ai_chat_send_message_no_api_key()
        results['ai_chat_with_mock'] = test_ai_chat_send_message_with_mock()
        results['ai_chat_error_handling'] = test_ai_chat_send_message_error_handling()
        results['services_imports'] = test_services_imports()
    except Exception as e:
        print(f'\n✗ Services tests failed with exception: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Run components tests
    print('\n' + '-' * 70)
    print('COMPONENTS TESTS (components/)')
    print('-' * 70)

    try:
        results['components_imports'] = test_components_imports()
        results['parameters_build_updates'] = test_parameters_build_updates()
        results['parameters_apply_updates'] = test_parameters_apply_param_updates()
        results['parameters_apply_preset'] = test_parameters_apply_pending_preset()
        results['parameters_apply_fit'] = test_parameters_apply_fit_results()
        results['parameters_apply_fit_no_pending'] = test_parameters_apply_fit_results_no_pending()
        results['fit_results_imports'] = test_fit_results_imports()
        results['fit_results_params_list'] = test_fit_results_build_fitted_params_list()
        results['fit_results_slider_range'] = test_fit_results_slider_range_calculation()
        results['fit_results_export'] = test_fit_results_export_data_structure()
        results['data_preview_imports'] = test_data_preview_imports()
        results['sidebar_imports'] = test_sidebar_imports()
    except Exception as e:
        print(f'\n✗ Components tests failed with exception: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Run openai_client tests
    print('\n' + '-' * 70)
    print('OPENAI CLIENT TESTS (openai_client.py)')
    print('-' * 70)

    try:
        results['openai_client_import'] = test_openai_client_import()
        results['openai_client_create'] = test_openai_client_create_chat_completion()
        results['openai_client_messages'] = test_openai_client_messages_conversion()
    except Exception as e:
        print(f'\n✗ OpenAI client tests failed with exception: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Run fitter integration tests
    print('\n' + '-' * 70)
    print('SANSFITTER INTEGRATION TESTS')
    print('-' * 70)

    try:
        results['fitter_integration'] = test_fitter_integration()
    except Exception as e:
        print(f'\n✗ Fitter integration tests failed with exception: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Run app module tests (requires Streamlit)
    print('\n' + '-' * 70)
    print('APP MODULE TESTS (app.py)')
    print('-' * 70)

    try:
        results['app_imports'] = test_app_imports()
        results['app_clamp'] = test_app_clamp_for_display()
    except Exception as e:
        print(f'\n✗ App module tests failed with exception: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Summary
    print('\n' + '=' * 70)
    print('TEST SUMMARY')
    print('=' * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = '✓ PASSED' if result else '✗ FAILED'
        print(f'  {test_name}: {status}')

    print(f'\nTotal: {passed}/{total} tests passed')

    if passed == total:
        print('\n' + '=' * 70)
        print('✓ All tests passed!')
        print('=' * 70)
        print('\nTo run the full Streamlit app, use:')
        print('  streamlit run src/app.py')
        print('=' * 70)
    else:
        print('\n✗ Some tests failed!')
        sys.exit(1)
