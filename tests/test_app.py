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
from sans_fitter import SANSFitter

import sans_analysis_utils as utils

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
        results['ai_chat_service'] = test_ai_chat_service()
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
    except Exception as e:
        print(f'\n✗ Components tests failed with exception: {e}')
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
