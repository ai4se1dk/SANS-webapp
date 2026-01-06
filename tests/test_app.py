#!/usr/bin/env python
"""
Test script to validate the SANS analysis utilities and Streamlit app functionality.

This test suite covers:
1. Utility functions (sans_analysis_utils.py) - no Streamlit dependency
2. App module imports and functions (app.py) - requires Streamlit
3. SANSFitter integration
"""

import sys

import numpy as np

sys.path.insert(0, '.')
sys.path.insert(0, 'src')

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

        # Check that app imports the utility functions
        assert hasattr(app, 'get_all_models'), 'get_all_models not available in app!'
        assert hasattr(app, 'analyze_data_for_ai_suggestion'), (
            'analyze_data_for_ai_suggestion not available in app!'
        )
        assert hasattr(app, 'suggest_models_simple'), 'suggest_models_simple not available in app!'
        assert hasattr(app, 'plot_data_and_fit'), 'plot_data_and_fit not available in app!'
        print('✓ Utility functions imported into app')

        # Check app-specific functions
        assert hasattr(app, 'suggest_models_ai'), 'suggest_models_ai not found in app!'
        assert hasattr(app, 'main'), 'main function not found in app!'
        assert hasattr(app, 'clamp_for_display'), 'clamp_for_display not found in app!'
        print('✓ App-specific functions available')

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
# Main Test Runner
# =============================================================================

if __name__ == '__main__':
    print('=' * 70)
    print('SANS Analysis - Test Suite')
    print('=' * 70)
    print('\nThis test covers both utility functions and the Streamlit app module.')

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
