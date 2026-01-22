"""
Integration tests for polydispersity support in SANS webapp.

Tests cover:
- Polydispersity UI constants
- Polydispersity parameter table rendering
- Session state management for PD
- PD parameter application to fitter
- Full workflow: model selection → enable PD → configure PD → fit
"""

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sans_fitter import SANSFitter

from sans_webapp.components.parameters import (
    apply_pd_updates,
    render_polydispersity_tab,
    render_polydispersity_table,
)
from sans_webapp.services.session_state import clear_parameter_state
from sans_webapp.ui_constants import (
    PARAM_TAB_BASIC,
    PARAM_TAB_POLYDISPERSITY,
    PD_DISTRIBUTION_TYPES,
    PD_ENABLE_HELP,
    PD_ENABLE_LABEL,
    PD_INFO_HEADER,
    PD_INFO_TEXT,
    PD_NOT_SUPPORTED,
    PD_SUCCESS_UPDATED,
    PD_TABLE_COLUMNS,
    PD_UPDATE_BUTTON,
)


class TestPolydispersityUIConstants:
    """Test polydispersity UI constants."""

    def test_tab_labels_exist(self):
        """Test that tab labels are defined."""
        assert PARAM_TAB_BASIC is not None
        assert PARAM_TAB_POLYDISPERSITY is not None
        assert 'Basic' in PARAM_TAB_BASIC or 'Parameter' in PARAM_TAB_BASIC
        assert 'Polydispersity' in PARAM_TAB_POLYDISPERSITY

    def test_pd_enable_constants(self):
        """Test PD enable/disable constants."""
        assert PD_ENABLE_LABEL is not None
        assert PD_ENABLE_HELP is not None

    def test_pd_table_columns(self):
        """Test PD table columns are defined."""
        assert PD_TABLE_COLUMNS is not None
        assert len(PD_TABLE_COLUMNS) >= 4  # Parameter, Width, N, Type, Vary

    def test_pd_distribution_types(self):
        """Test distribution types list."""
        assert PD_DISTRIBUTION_TYPES is not None
        assert 'gaussian' in PD_DISTRIBUTION_TYPES
        assert 'lognormal' in PD_DISTRIBUTION_TYPES
        assert 'schulz' in PD_DISTRIBUTION_TYPES
        assert 'rectangle' in PD_DISTRIBUTION_TYPES
        assert 'boltzmann' in PD_DISTRIBUTION_TYPES

    def test_pd_info_constants(self):
        """Test PD info section constants."""
        assert PD_INFO_HEADER is not None
        assert PD_INFO_TEXT is not None
        assert len(PD_INFO_TEXT) > 50  # Should be informative

    def test_pd_messages(self):
        """Test PD message constants."""
        assert PD_NOT_SUPPORTED is not None
        assert PD_SUCCESS_UPDATED is not None
        assert PD_UPDATE_BUTTON is not None


class TestPolydispersitySessionState:
    """Test session state management for polydispersity."""

    def test_clear_parameter_state_clears_pd_keys(self):
        """Test that clear_parameter_state removes PD-related keys."""
        mock_session_state = {
            'fitter': MagicMock(),
            'data_loaded': True,
            'value_radius': 50.0,
            'vary_radius': True,
            # PD keys
            'pd_enabled': True,
            'pd_updates': {'radius': {'pd_width': 0.1}},
            'pd_width_radius': 0.1,
            'pd_n_radius': 35,
            'pd_type_radius': 'gaussian',
            'pd_vary_radius': True,
        }

        deleted_keys = []

        class MockSessionState:
            def keys(self):
                return list(mock_session_state.keys())

            def __delitem__(self, key):
                deleted_keys.append(key)
                del mock_session_state[key]

            def __contains__(self, key):
                return key in mock_session_state

        with patch('sans_webapp.services.session_state.st') as mock_st:
            mock_st.session_state = MockSessionState()

            clear_parameter_state()

            # Verify PD keys were deleted
            assert 'pd_enabled' in deleted_keys
            assert 'pd_updates' in deleted_keys
            assert 'pd_width_radius' in deleted_keys
            assert 'pd_n_radius' in deleted_keys
            assert 'pd_type_radius' in deleted_keys
            assert 'pd_vary_radius' in deleted_keys
            # Standard param keys also deleted
            assert 'value_radius' in deleted_keys
            assert 'vary_radius' in deleted_keys
            # Non-param keys preserved
            assert 'fitter' not in deleted_keys
            assert 'data_loaded' not in deleted_keys


class TestApplyPDUpdates:
    """Test apply_pd_updates function."""

    def test_apply_pd_updates_to_fitter(self):
        """Test that PD updates are correctly applied to fitter."""
        fitter = SANSFitter()
        fitter.set_model('sphere')

        pd_updates = {
            'radius': {
                'pd_width': 0.15,
                'pd_n': 40,
                'pd_type': 'lognormal',
                'vary': True,
            }
        }

        apply_pd_updates(fitter, pd_updates)

        pd_config = fitter.get_pd_param('radius')
        assert pd_config['pd'] == 0.15
        assert pd_config['pd_n'] == 40
        assert pd_config['pd_type'] == 'lognormal'
        assert pd_config['vary'] is True

    def test_apply_pd_updates_multiple_params(self):
        """Test applying PD updates to multiple parameters."""
        fitter = SANSFitter()
        fitter.set_model('cylinder')

        pd_updates = {
            'radius': {
                'pd_width': 0.1,
                'pd_n': 35,
                'pd_type': 'gaussian',
                'vary': True,
            },
            'length': {
                'pd_width': 0.2,
                'pd_n': 50,
                'pd_type': 'schulz',
                'vary': False,
            },
        }

        apply_pd_updates(fitter, pd_updates)

        radius_pd = fitter.get_pd_param('radius')
        assert radius_pd['pd'] == 0.1
        assert radius_pd['pd_type'] == 'gaussian'
        assert radius_pd['vary'] is True

        length_pd = fitter.get_pd_param('length')
        assert length_pd['pd'] == 0.2
        assert length_pd['pd_n'] == 50
        assert length_pd['pd_type'] == 'schulz'
        assert length_pd['vary'] is False


class TestPolydispersityWorkflow:
    """Test complete polydispersity workflow integration."""

    def test_full_pd_workflow_with_fitting(self):
        """Test full workflow: load data → set model → enable PD → configure → fit."""
        import os
        import tempfile

        # Create test data file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_file.write('Q,I,dI\n')
        q = np.logspace(-2, 0, 30)
        intensity = 0.01 * (1 / (1 + (q * 50) ** 2)) + 0.001
        d_intensity = intensity * 0.1
        for qi, intensity_i, d_intensity_i in zip(q, intensity, d_intensity):
            temp_file.write(f'{qi},{intensity_i},{d_intensity_i}\n')
        temp_file.close()

        try:
            # 1. Initialize fitter and load data
            fitter = SANSFitter()
            fitter.load_data(temp_file.name)

            # 2. Set model
            fitter.set_model('sphere')
            assert fitter.supports_polydispersity()

            # 3. Configure basic parameters
            fitter.set_param('radius', value=50.0, min=10.0, max=100.0, vary=True)
            fitter.set_param('scale', value=0.01, min=0.001, max=1.0, vary=True)
            fitter.set_param('background', value=0.001, min=0, max=0.1, vary=True)
            fitter.set_param('sld', value=4.0, vary=False)
            fitter.set_param('sld_solvent', value=1.0, vary=False)

            # 4. Enable polydispersity
            fitter.enable_polydispersity(True)
            assert fitter.is_polydispersity_enabled()

            # 5. Configure PD parameters (simulating what apply_pd_updates does)
            pd_updates = {
                'radius': {
                    'pd_width': 0.1,
                    'pd_n': 35,
                    'pd_type': 'gaussian',
                    'vary': True,
                }
            }
            apply_pd_updates(fitter, pd_updates)

            # 6. Verify PD configuration
            pd_config = fitter.get_pd_param('radius')
            assert pd_config['pd'] == 0.1
            assert pd_config['vary'] is True

            # 7. Fit with polydispersity
            result = fitter.fit(engine='bumps', method='amoeba')
            assert result is not None
            assert 'chisq' in result
            assert 'radius_pd' in result['parameters']

        finally:
            os.unlink(temp_file.name)

    def test_pd_disabled_excludes_from_fit(self):
        """Test that PD params are excluded when polydispersity is disabled."""
        import os
        import tempfile

        # Create test data file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_file.write('Q,I,dI\n')
        q = np.logspace(-2, 0, 30)
        intensity = 0.01 * (1 / (1 + (q * 50) ** 2)) + 0.001
        d_intensity = intensity * 0.1
        for qi, intensity_i, d_intensity_i in zip(q, intensity, d_intensity):
            temp_file.write(f'{qi},{intensity_i},{d_intensity_i}\n')
        temp_file.close()

        try:
            fitter = SANSFitter()
            fitter.load_data(temp_file.name)
            fitter.set_model('sphere')

            # Configure parameters
            fitter.set_param('radius', value=50.0, min=10.0, max=100.0, vary=True)
            fitter.set_param('scale', value=0.01, vary=True)
            fitter.set_param('background', value=0.001, vary=True)
            fitter.set_param('sld', value=4.0, vary=False)
            fitter.set_param('sld_solvent', value=1.0, vary=False)

            # Configure PD but keep disabled
            fitter.set_pd_param('radius', pd_width=0.1, vary=True)
            fitter.enable_polydispersity(False)

            # Fit
            result = fitter.fit(engine='bumps', method='amoeba')
            assert result is not None

            # PD params should NOT be in results
            assert 'radius_pd' not in result['parameters']

        finally:
            os.unlink(temp_file.name)


class TestPolydispersityMultipleModels:
    """Test polydispersity with different model types."""

    def test_sphere_pd_params(self):
        """Test sphere model polydispersity parameters."""
        fitter = SANSFitter()
        fitter.set_model('sphere')

        assert fitter.supports_polydispersity()
        pd_params = fitter.get_polydisperse_parameters()
        assert 'radius' in pd_params

    def test_cylinder_pd_params(self):
        """Test cylinder model polydispersity parameters."""
        fitter = SANSFitter()
        fitter.set_model('cylinder')

        assert fitter.supports_polydispersity()
        pd_params = fitter.get_polydisperse_parameters()
        assert 'radius' in pd_params
        assert 'length' in pd_params

    def test_ellipsoid_pd_params(self):
        """Test ellipsoid model polydispersity parameters."""
        fitter = SANSFitter()
        fitter.set_model('ellipsoid')

        assert fitter.supports_polydispersity()
        pd_params = fitter.get_polydisperse_parameters()
        # Ellipsoid has radius_polar and radius_equatorial
        assert len(pd_params) >= 2

    def test_core_shell_sphere_pd_params(self):
        """Test core_shell_sphere model polydispersity parameters."""
        fitter = SANSFitter()
        fitter.set_model('core_shell_sphere')

        assert fitter.supports_polydispersity()
        pd_params = fitter.get_polydisperse_parameters()
        assert len(pd_params) >= 1

    def test_model_switch_resets_pd(self):
        """Test that switching models resets polydispersity state."""
        fitter = SANSFitter()
        fitter.set_model('sphere')

        # Configure PD
        fitter.set_pd_param('radius', pd_width=0.2, pd_type='lognormal')
        fitter.enable_polydispersity(True)

        # Switch model
        fitter.set_model('cylinder')

        # PD should be reset
        assert not fitter.is_polydispersity_enabled()
        pd_config = fitter.get_pd_param('radius')
        assert pd_config['pd'] == 0.0  # Back to default


class TestPolydispersityDistributionTypes:
    """Test different polydispersity distribution types."""

    def test_gaussian_distribution(self):
        """Test setting Gaussian distribution."""
        fitter = SANSFitter()
        fitter.set_model('sphere')
        fitter.set_pd_param('radius', pd_width=0.1, pd_type='gaussian')

        pd_config = fitter.get_pd_param('radius')
        assert pd_config['pd_type'] == 'gaussian'

    def test_lognormal_distribution(self):
        """Test setting lognormal distribution."""
        fitter = SANSFitter()
        fitter.set_model('sphere')
        fitter.set_pd_param('radius', pd_width=0.1, pd_type='lognormal')

        pd_config = fitter.get_pd_param('radius')
        assert pd_config['pd_type'] == 'lognormal'

    def test_schulz_distribution(self):
        """Test setting Schulz distribution."""
        fitter = SANSFitter()
        fitter.set_model('sphere')
        fitter.set_pd_param('radius', pd_width=0.1, pd_type='schulz')

        pd_config = fitter.get_pd_param('radius')
        assert pd_config['pd_type'] == 'schulz'

    def test_rectangle_distribution(self):
        """Test setting rectangle distribution."""
        fitter = SANSFitter()
        fitter.set_model('sphere')
        fitter.set_pd_param('radius', pd_width=0.1, pd_type='rectangle')

        pd_config = fitter.get_pd_param('radius')
        assert pd_config['pd_type'] == 'rectangle'

    def test_boltzmann_distribution(self):
        """Test setting Boltzmann distribution."""
        fitter = SANSFitter()
        fitter.set_model('sphere')
        fitter.set_pd_param('radius', pd_width=0.1, pd_type='boltzmann')

        pd_config = fitter.get_pd_param('radius')
        assert pd_config['pd_type'] == 'boltzmann'

    def test_invalid_distribution_raises_error(self):
        """Test that invalid distribution type raises error."""
        fitter = SANSFitter()
        fitter.set_model('sphere')

        with pytest.raises(ValueError):
            fitter.set_pd_param('radius', pd_type='invalid_distribution')


class TestPolydispersityWithStructureFactor:
    """Test polydispersity combined with structure factors."""

    def test_pd_with_hardsphere_structure(self):
        """Test polydispersity with hardsphere structure factor."""
        import os
        import tempfile

        # Create test data
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_file.write('Q,I,dI\n')
        q = np.logspace(-2, 0, 30)
        intensity = 0.01 * (1 / (1 + (q * 50) ** 2)) + 0.001
        d_intensity = intensity * 0.1
        for qi, intensity_i, d_intensity_i in zip(q, intensity, d_intensity):
            temp_file.write(f'{qi},{intensity_i},{d_intensity_i}\n')
        temp_file.close()

        try:
            fitter = SANSFitter()
            fitter.load_data(temp_file.name)
            fitter.set_model('sphere')

            # Add structure factor
            fitter.set_structure_factor('hardsphere')
            fitter.set_param('volfraction', value=0.2, min=0.0, max=0.6, vary=True)

            # Configure PD
            fitter.enable_polydispersity(True)
            fitter.set_pd_param('radius', pd_width=0.1, vary=False)

            # Set up remaining params
            fitter.set_param('radius', value=50.0, min=10.0, max=100.0, vary=True)
            fitter.set_param('scale', value=0.01, vary=True)
            fitter.set_param('background', value=0.001, vary=True)
            fitter.set_param('radius_effective', value=50.0, vary=True)

            # Fit should work with both PD and structure factor
            result = fitter.fit(engine='bumps', method='amoeba')
            assert result is not None
            assert 'chisq' in result
            assert 'volfraction' in result['parameters']

        finally:
            os.unlink(temp_file.name)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
