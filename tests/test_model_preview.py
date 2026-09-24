"""
Tests for the model preview: sans-fitter's plot_model()/compare() wrappers in
``sans_analysis_utils`` and the snapshot bookkeeping in the component.
"""

from unittest.mock import patch

import pytest
from sans_fitter import SANSFitter

from sans_webapp import sans_analysis_utils as utils
from sans_webapp.components import model_preview

EXAMPLE_DATA = 'simulated_sans_data.csv'


@pytest.fixture
def sphere_fitter():
    fitter = SANSFitter()
    fitter.load_data(EXAMPLE_DATA)
    fitter.set_model('sphere')
    return fitter


@pytest.fixture
def session_state():
    state: dict = {}
    with patch.object(model_preview.st, 'session_state', state):
        yield state


class TestModelPreviewPlot:
    def test_preview_before_any_fit(self, sphere_fitter):
        fig = utils.plot_model_preview(sphere_fitter)
        assert fig.layout.title.text.startswith('Model preview')
        assert 'yaxis2' in fig.layout
        assert fig.layout.width is None

    def test_preview_follows_parameter_changes(self, sphere_fitter):
        before = utils.plot_model_preview(sphere_fitter, show_residuals=False)
        sphere_fitter.set_param('radius', value=sphere_fitter.params['radius']['value'] * 2)
        after = utils.plot_model_preview(sphere_fitter, show_residuals=False)
        curve_before = [t for t in before.data if t.mode == 'lines'][0].y
        curve_after = [t for t in after.data if t.mode == 'lines'][0].y
        assert list(curve_before) != list(curve_after)

    def test_preview_options(self, sphere_fitter):
        fig = utils.plot_model_preview(sphere_fitter, show_residuals=False, log_scale=False)
        assert 'yaxis2' not in fig.layout
        assert fig.layout.xaxis.type == 'linear'


class TestSnapshots:
    def test_snapshot_captures_current_values(self, sphere_fitter):
        values = utils.snapshot_parameters(sphere_fitter)
        assert set(values) == set(sphere_fitter.params)
        assert values['radius'] == sphere_fitter.params['radius']['value']

    def test_snapshot_includes_pd_widths_when_enabled(self, sphere_fitter):
        assert 'radius_pd' not in utils.snapshot_parameters(sphere_fitter)
        sphere_fitter.enable_polydispersity(True)
        sphere_fitter.set_pd_param('radius', pd_width=0.1)
        assert utils.snapshot_parameters(sphere_fitter)['radius_pd'] == pytest.approx(0.1)

    def test_comparison_overlays_current_and_snapshots(self, sphere_fitter):
        first = utils.snapshot_parameters(sphere_fitter)
        sphere_fitter.set_param('radius', value=first['radius'] * 1.5)
        fig = utils.plot_parameter_comparison(sphere_fitter, {'start': first})
        names = [trace.name for trace in fig.data]
        assert names == ['Experimental Data', utils.CURRENT_PARAMETERS_LABEL, 'start']
        # compare() evaluates the snapshot without touching the fitter
        assert sphere_fitter.params['radius']['value'] == first['radius'] * 1.5

    def test_comparison_without_current(self, sphere_fitter):
        snap = utils.snapshot_parameters(sphere_fitter)
        fig = utils.plot_parameter_comparison(sphere_fitter, {'a': snap}, include_current=False)
        assert [trace.name for trace in fig.data] == ['Experimental Data', 'a']

    def test_add_snapshot_labels(self, sphere_fitter, session_state):
        assert model_preview.add_snapshot(sphere_fitter) == 'Snapshot 1'
        assert model_preview.add_snapshot(sphere_fitter, '  thin  ') == 'thin'
        assert model_preview.add_snapshot(sphere_fitter, 'thin') == 'thin (2)'
        assert list(model_preview.get_snapshots(sphere_fitter)) == [
            'Snapshot 1',
            'thin',
            'thin (2)',
        ]

    def test_snapshots_reset_when_model_changes(self, sphere_fitter, session_state):
        model_preview.add_snapshot(sphere_fitter)
        assert model_preview.get_snapshots(sphere_fitter)
        sphere_fitter.set_model('cylinder')
        assert model_preview.get_snapshots(sphere_fitter) == {}
