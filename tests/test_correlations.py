"""
Tests for the parameter correlation heatmap shown after a fit.
"""

import numpy as np
import pytest
from sans_fitter import SANSFitter

from sans_webapp.components.correlations import plot_correlation_matrix

EXAMPLE_DATA = 'simulated_sans_data.csv'


@pytest.fixture(scope='module')
def fitted_report():
    fitter = SANSFitter()
    fitter.load_data(EXAMPLE_DATA)
    fitter.set_model('sphere')
    fitter.set_param('scale', value=1.0, min=0.01, max=10.0, vary=True)
    fitter.set_param('background', value=0.001, min=0.0, max=1.0, vary=True)
    fitter.set_param('radius', value=40.0, min=5.0, max=200.0, vary=True)
    fitter.fit(engine='bumps', method='amoeba')
    return fitter.get_fit_report()


def test_fit_report_exposes_correlations(fitted_report):
    assert fitted_report.corr is not None
    assert len(fitted_report.cov_labels) == 3
    assert fitted_report.corr.shape == (3, 3)


def test_heatmap_shows_strict_lower_triangle(fitted_report):
    labels = list(fitted_report.cov_labels)
    fig = plot_correlation_matrix(labels, fitted_report.corr)
    heatmap = fig.data[0]
    z = np.array(heatmap.z, dtype=float)
    # Row i of the heatmap is labels[i + 1], column j is labels[j]
    assert list(heatmap.y) == labels[1:] and list(heatmap.x) == labels[:-1]
    for i in range(len(labels) - 1):
        for j in range(len(labels) - 1):
            if j <= i:
                assert z[i, j] == pytest.approx(fitted_report.corr[i + 1, j])
            else:
                assert np.isnan(z[i, j])
    assert (heatmap.zmin, heatmap.zmax) == (-1, 1)


def test_heatmap_labels_cells():
    corr = np.array([[1.0, -0.97], [-0.97, 1.0]])
    fig = plot_correlation_matrix(['a', 'b'], corr)
    assert np.array(fig.data[0].text).tolist() == [['-0.97']]
    # The input matrix is left untouched
    assert corr[0, 1] == -0.97


# -----------------------------------------------------------------------------
# render_parameter_correlations(): skip conditions, warnings, initial state
# -----------------------------------------------------------------------------


def _render_app():
    """Render the section for a stub fitter whose report is set in session state."""
    import streamlit as st

    from sans_webapp.components.correlations import render_parameter_correlations

    case = st.session_state.case

    class Report:
        corr = case['corr']
        cov_labels = case['labels']
        cov_source = 'jacobian'

        def strongly_correlated(self):
            return case['pairs']

    class Fitter:
        def get_fit_report(self):
            if case.get('no_fit'):
                raise ValueError('No fit results available.')
            return Report()

    render_parameter_correlations(Fitter())


def _run(case):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_render_app, default_timeout=30)
    at.session_state['case'] = case
    return at.run()


@pytest.mark.parametrize(
    'case',
    [
        {'no_fit': True, 'corr': None, 'labels': [], 'pairs': []},
        {'corr': None, 'labels': ['a', 'b'], 'pairs': []},
        {'corr': np.eye(1), 'labels': ['a'], 'pairs': []},
    ],
    ids=['no-fit', 'no-covariance', 'one-parameter'],
)
def test_section_skipped_without_usable_correlations(case):
    at = _run(case)
    assert not at.exception
    assert len(at.expander) == 0
    assert len(at.get('plotly_chart')) == 0


def test_weak_correlations_render_collapsed_without_warnings():
    at = _run({'corr': np.array([[1.0, 0.3], [0.3, 1.0]]), 'labels': ['a', 'b'], 'pairs': []})
    assert not at.exception
    assert at.expander[0].proto.expanded is False
    assert len(at.warning) == 0
    assert len(at.get('plotly_chart')) == 1


def test_strong_correlations_warn_with_sign_and_open_the_section():
    corr = np.array([[1.0, 0.95, -0.95], [0.95, 1.0, 0.1], [-0.95, 0.1, 1.0]])
    pairs = [('a', 'b', 0.95), ('a', 'c', -0.95)]
    at = _run({'corr': corr, 'labels': ['a', 'b', 'c'], 'pairs': pairs})
    assert not at.exception
    assert at.expander[0].proto.expanded is True
    warnings = [w.value for w in at.warning]
    assert warnings == [
        'a and b are strongly correlated (ρ = +0.950)',
        'a and c are strongly correlated (ρ = -0.950)',
    ]
    assert len(at.get('plotly_chart')) == 1


def _fit_results_app():
    import streamlit as st
    from sans_fitter import SANSFitter

    from sans_webapp.components.fit_results import render_fit_results

    if 'fitter' not in st.session_state:
        fitter = SANSFitter()
        fitter.load_data('simulated_sans_data.csv')
        fitter.set_model('sphere')
        fitter.set_param('scale', value=1.0, min=0.01, max=10.0, vary=True)
        fitter.set_param('background', value=0.001, min=0.0, max=1.0, vary=True)
        fitter.set_param('radius', value=40.0, min=5.0, max=200.0, vary=True)
        st.session_state.fit_result = fitter.fit(engine='bumps', method='amoeba')
        st.session_state.fitter = fitter
        st.session_state.fit_completed = True
    render_fit_results(st.session_state.fitter, {})


def test_fit_results_section_includes_correlations():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_fit_results_app, default_timeout=60).run()
    assert not at.exception
    assert [e.value for e in at.error] == []
    labels = [e.label for e in at.expander]
    assert any('Parameter Correlations' in label for label in labels)
    # Data/fit plot and correlation heatmap
    assert len(at.get('plotly_chart')) == 2
