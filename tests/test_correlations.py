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
