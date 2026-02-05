"""
Shared pytest fixtures for SANS-webapp tests.
"""

from unittest.mock import MagicMock

import numpy as np
import pytest


class MockSessionState:
    """Mock for Streamlit session_state."""

    def __init__(self):
        self._data = {
            'ai_tools_enabled': True,
            'needs_rerun': False,
            'current_model': None,
            'model_selected': False,
            'data_loaded': False,
            'fit_completed': False,
            'fit_status': 'idle',
            'fit_result': None,
            'fit_error': None,
            'chat_history': [],
            'chat_api_key': None,
            'show_ai_chat': True,
            'expand_data_upload': True,
            'expand_model_selection': False,
            'expand_fitting': False,
            'fitter': None,
        }

    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data

    def keys(self):
        return self._data.keys()

    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]


class MockFitter:
    """Mock for SANSFitter."""

    def __init__(self):
        self.model = None
        self.data = None
        self.params = {}
        self.result = None

    def set_model(self, model_name: str):
        self.model = MagicMock()
        self.model.name = model_name
        self.params = {
            'radius': MagicMock(value=50.0, bounds=(1, 500), vary=True),
            'sld': MagicMock(value=1e-6, bounds=(0, 1e-5), vary=True),
            'sld_solvent': MagicMock(value=6e-6, bounds=(0, 1e-5), vary=False),
            'background': MagicMock(value=0.001, bounds=(0, 1), vary=True),
        }
        return self

    def load_data(self, path: str):
        self.data = MagicMock()
        self.data.x = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        self.data.y = np.array([100.0, 50.0, 25.0, 12.5, 6.25])
        self.data.dy = np.array([1.0, 0.5, 0.25, 0.125, 0.0625])
        return self

    def fit(self):
        result = MagicMock()
        result.redchi = 1.5
        result.params = self.params.copy()
        self.result = result
        return result

    def enable_polydispersity(self, param_name: str, pd_type: str = 'gaussian'):
        return self

    def set_structure_factor(self, sf_name: str):
        return self

    def remove_structure_factor(self):
        return self


@pytest.fixture
def mock_session_state():
    """Create a fresh mock session state."""
    return MockSessionState()


@pytest.fixture
def mock_fitter():
    """Create a fresh mock fitter."""
    return MockFitter()


@pytest.fixture
def mock_fitter_with_model():
    """Create a mock fitter with a model already loaded."""
    fitter = MockFitter()
    fitter.set_model('sphere')
    return fitter


@pytest.fixture
def mock_fitter_with_data():
    """Create a mock fitter with data loaded."""
    fitter = MockFitter()
    fitter.load_data('test_data.csv')
    return fitter


@pytest.fixture
def mock_fitter_full():
    """Create a mock fitter with both model and data."""
    fitter = MockFitter()
    fitter.load_data('test_data.csv')
    fitter.set_model('sphere')
    return fitter
