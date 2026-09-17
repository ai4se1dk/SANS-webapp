"""
Shared pytest fixtures for SANS-webapp tests.

``MockFitter`` mirrors the public surface of ``sans_fitter.SANSFitter`` (>= 0.4)
that the webapp relies on: parameter dictionaries, polydispersity configured
through ``set_pd_param``/``get_pd_param`` (not through ``params``), the fit Q
range API, and ``fit()`` returning a result dictionary with ``reduced_chisq``
and a full ``parameters`` block carrying ``fixed`` flags.
"""

from typing import Any
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

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data

    def keys(self):
        return self._data.keys()

    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]


_PD_DEFAULTS = {'pd': 0.0, 'pd_n': 35, 'pd_nsigma': 3.0, 'pd_type': 'gaussian', 'vary': False}
_PD_TYPES = ('gaussian', 'rectangle', 'lognormal', 'schulz', 'boltzmann')

MOCK_REDUCED_CHISQ = 1.5


class MockFitter:
    """Mock for SANSFitter (sans-fitter >= 0.4 API surface)."""

    def __init__(self):
        self.kernel = None
        self.model_name = None
        self.data = None
        self.params: dict[str, dict] = {}
        self.fit_result: dict[str, Any] | None = None
        self._pd_params: dict[str, dict[str, Any]] = {}
        self._pd_enabled = False
        self._structure_factor: str | None = None
        self._q_range: tuple[float, float] | None = None
        self._full_q_range: tuple[float, float] | None = None

    # ------------------------------------------------------------------ model

    def set_model(self, model_name: str):
        self.kernel = MagicMock()
        self.model_name = model_name
        self.params = {
            'radius': {'value': 50.0, 'min': 1, 'max': 500, 'vary': True, 'description': ''},
            'sld': {'value': 1e-6, 'min': 0, 'max': 1e-5, 'vary': True, 'description': ''},
            'sld_solvent': {'value': 6e-6, 'min': 0, 'max': 1e-5, 'vary': False, 'description': ''},
            'background': {'value': 0.001, 'min': 0, 'max': 1, 'vary': True, 'description': ''},
            'scale': {'value': 1.0, 'min': 0.001, 'max': 10, 'vary': True, 'description': ''},
        }
        self._pd_params = {'radius': dict(_PD_DEFAULTS)}
        self._pd_enabled = False
        self._structure_factor = None
        self.fit_result = None
        return self

    def set_param(self, name: str, **kwargs):
        if name not in self.params:
            raise KeyError(f'Unknown parameter: {name}')
        for key in ('value', 'min', 'max', 'vary'):
            if key in kwargs and kwargs[key] is not None:
                self.params[name][key] = kwargs[key]

    # ------------------------------------------------------------------- data

    def load_data(self, path: str, dataset: int | str = 0):
        self.data = MagicMock()
        self.data.x = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        self.data.y = np.array([100.0, 50.0, 25.0, 12.5, 6.25])
        self.data.dy = np.array([1.0, 0.5, 0.25, 0.125, 0.0625])
        self.data.dx = np.zeros(5)
        self._full_q_range = (0.01, 0.05)
        self._q_range = self._full_q_range
        self.data.qmin, self.data.qmax = self._q_range
        return self

    def get_q_range(self):
        return self._q_range

    def set_q_range(self, qmin: float | None = None, qmax: float | None = None) -> None:
        if self.data is None:
            raise ValueError('No data loaded. Use load_data() first.')
        if qmin is None and qmax is None:
            raise ValueError('Provide qmin, qmax, or both.')
        full_min, full_max = self._full_q_range
        new_min = full_min if qmin is None else float(qmin)
        new_max = full_max if qmax is None else float(qmax)
        if new_min >= new_max:
            raise ValueError(f'qmin ({new_min:g}) must be smaller than qmax ({new_max:g}).')
        self._q_range = (new_min, new_max)
        self.data.qmin, self.data.qmax = self._q_range

    def reset_q_range(self) -> None:
        if self.data is None:
            raise ValueError('No data loaded. Use load_data() first.')
        self._q_range = self._full_q_range
        self.data.qmin, self.data.qmax = self._q_range

    def get_resolution(self) -> dict[str, Any]:
        return {'mode': 'data', 'dq_over_q': None, 'slit_length': None, 'slit_width': None}

    # ------------------------------------------------------------ polydispersity

    def supports_polydispersity(self) -> bool:
        return bool(self._pd_params)

    def get_polydisperse_parameters(self) -> list[str]:
        return list(self._pd_params.keys())

    def get_pd_param(self, name: str) -> dict[str, Any]:
        if name not in self._pd_params:
            raise KeyError(f"'{name}' is not a polydisperse parameter")
        config = dict(self._pd_params[name])
        config['active'] = config['pd'] > 0
        return config

    def set_pd_param(
        self,
        name: str,
        pd_width: float | None = None,
        pd_n: int | None = None,
        pd_nsigma: float | None = None,
        pd_type: str | None = None,
        vary: bool | None = None,
    ) -> None:
        if name not in self._pd_params:
            raise KeyError(f"'{name}' is not a polydisperse parameter")
        if pd_type is not None and pd_type not in _PD_TYPES:
            raise ValueError(f"Invalid pd_type '{pd_type}'. Use one of {_PD_TYPES}")
        config = self._pd_params[name]
        if pd_width is not None:
            config['pd'] = float(pd_width)
        if pd_n is not None:
            config['pd_n'] = int(pd_n)
        if pd_nsigma is not None:
            config['pd_nsigma'] = float(pd_nsigma)
        if pd_type is not None:
            config['pd_type'] = pd_type
        if vary is not None:
            config['vary'] = bool(vary)

    def enable_polydispersity(self, enabled: bool = True) -> None:
        self._pd_enabled = bool(enabled)

    def is_polydispersity_enabled(self) -> bool:
        return self._pd_enabled

    def get_varying_pd_params(self) -> list[str]:
        if not self._pd_enabled:
            return []
        return [f'{name}_pd' for name, cfg in self._pd_params.items() if cfg.get('vary')]

    # ---------------------------------------------------------- structure factor

    def get_structure_factor(self) -> str | None:
        return self._structure_factor

    def set_structure_factor(self, sf_name: str, radius_effective_mode: str = 'unconstrained'):
        if self.kernel is None:
            raise ValueError('No form factor model loaded. Use set_model() first.')
        self._structure_factor = sf_name
        self.params.setdefault(
            'volfraction', {'value': 0.2, 'min': 0, 'max': 0.74, 'vary': False, 'description': ''}
        )
        self.params.setdefault(
            'radius_effective',
            {'value': 50.0, 'min': 0, 'max': 1000, 'vary': False, 'description': ''},
        )
        return self

    def remove_structure_factor(self):
        if self._structure_factor is None:
            raise ValueError('No structure factor is currently set.')
        self._structure_factor = None
        self.params.pop('volfraction', None)
        self.params.pop('radius_effective', None)
        return self

    def get_links(self) -> dict[str, str]:
        return {}

    def get_components(self) -> list[tuple[str, str, str]]:
        return []

    # ---------------------------------------------------------------- fitting

    def fit(self, engine: str = 'bumps', method: str | None = None, **kwargs) -> dict[str, Any]:
        """Return a sans-fitter >= 0.4 shaped result built from the current values."""
        if self.data is None:
            raise ValueError('No data loaded. Use load_data() first.')
        if self.kernel is None:
            raise ValueError('No model loaded. Use set_model() first.')

        parameters: dict[str, dict[str, Any]] = {}
        for name, info in self.params.items():
            varied = bool(info.get('vary', False))
            value = float(info['value'])
            stderr = 0.1 * abs(value) if varied else 0.0
            parameters[name] = {
                'value': value,
                'stderr': stderr,
                'formatted': f'{value:.6g} ± {stderr:.3g}' if varied else f'{value:.6g} (fixed)',
                'fixed': not varied,
                'linked_to': None,
            }
        for pd_name in self.get_varying_pd_params():
            width = float(self._pd_params[pd_name[:-3]]['pd'])
            parameters[pd_name] = {
                'value': width,
                'stderr': 0.01,
                'formatted': f'{width:.6g} ± 0.01',
                'fixed': False,
                'linked_to': None,
            }

        n_points = int(len(self.data.x))
        n_free = sum(1 for info in parameters.values() if not info['fixed'])
        dof = n_points - n_free
        self.fit_result = {
            'engine': engine,
            'method': method or ('amoeba' if engine == 'bumps' else 'leastsq'),
            'chisq': MOCK_REDUCED_CHISQ * dof,
            'reduced_chisq': MOCK_REDUCED_CHISQ,
            'n_points': n_points,
            'n_free': n_free,
            'dof': dof,
            'converged': None if engine == 'bumps' else True,
            'message': '',
            'weighting_note': 'dI',
            'cov': None,
            'cov_labels': [name for name, info in parameters.items() if not info['fixed']],
            'cov_source': None,
            'on_bounds': [],
            'parameters': parameters,
        }
        return self.fit_result

    def calculate(self, q=None, dq=None) -> np.ndarray:
        if self.data is None and q is None:
            raise ValueError('No data loaded. Use load_data() first.')
        grid = np.asarray(self.data.x if q is None else q, dtype=float)
        return np.ones_like(grid)

    def get_fit_report(self):
        if self.fit_result is None:
            raise ValueError('No fit result available. Run fit() first.')
        report = MagicMock()
        report.to_markdown.return_value = '| Parameter | Value |\n|---|---|\n'
        return report


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
