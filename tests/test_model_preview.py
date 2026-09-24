"""
Tests for the model preview: sans-fitter's plot_model()/compare() wrappers in
``sans_analysis_utils`` and the snapshot bookkeeping in the component.
"""

from unittest.mock import patch

import numpy as np
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


def _curves(fig):
    """Model curves of a comparison figure, by label (data trace left out)."""
    return {t.name: np.asarray(t.y, dtype=float) for t in fig.data if t.mode == 'lines'}


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
        assert set(values) == set(sphere_fitter.params) | {'radius_pd'}
        assert values['radius'] == sphere_fitter.params['radius']['value']

    def test_snapshot_pins_pd_widths(self, sphere_fitter):
        # Disabled: widths pinned to zero, whatever the stored width is
        sphere_fitter.set_pd_param('radius', pd_width=0.3)
        assert utils.snapshot_parameters(sphere_fitter)['radius_pd'] == 0.0
        sphere_fitter.enable_polydispersity(True)
        sphere_fitter.set_pd_param('radius', pd_width=0.1)
        assert utils.snapshot_parameters(sphere_fitter)['radius_pd'] == pytest.approx(0.1)

    def test_monodisperse_snapshot_survives_enabling_pd(self, sphere_fitter):
        saved_curve = sphere_fitter.calculate().copy()
        snapshot = utils.snapshot_parameters(sphere_fitter)
        sphere_fitter.enable_polydispersity(True)
        sphere_fitter.set_pd_param('radius', pd_width=0.2)
        curves = _curves(utils.plot_parameter_comparison(sphere_fitter, {'mono': snapshot}))
        np.testing.assert_allclose(curves['mono'], saved_curve)
        assert not np.allclose(curves[utils.CURRENT_PARAMETERS_LABEL], saved_curve)

    def test_polydisperse_snapshot_survives_disabling_pd(self, sphere_fitter):
        sphere_fitter.enable_polydispersity(True)
        sphere_fitter.set_pd_param('radius', pd_width=0.2)
        saved_curve = sphere_fitter.calculate().copy()
        snapshot = utils.snapshot_parameters(sphere_fitter)
        sphere_fitter.enable_polydispersity(False)
        curves = _curves(utils.plot_parameter_comparison(sphere_fitter, {'poly': snapshot}))
        np.testing.assert_allclose(curves['poly'], saved_curve)
        assert not np.allclose(curves[utils.CURRENT_PARAMETERS_LABEL], saved_curve)

    def test_snapshot_named_like_current_keeps_both_curves(self, sphere_fitter):
        saved_curve = sphere_fitter.calculate().copy()
        snapshot = utils.snapshot_parameters(sphere_fitter)
        sphere_fitter.set_param('radius', value=30.0)
        label = utils.CURRENT_PARAMETERS_LABEL
        curves = _curves(utils.plot_parameter_comparison(sphere_fitter, {label: snapshot}))
        assert list(curves) == [label, f'{label} (2)']
        np.testing.assert_allclose(curves[label], sphere_fitter.calculate())
        np.testing.assert_allclose(curves[f'{label} (2)'], saved_curve)

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

    def test_snapshot_label_cannot_take_current_label(self, sphere_fitter, session_state):
        label = utils.CURRENT_PARAMETERS_LABEL
        assert model_preview.add_snapshot(sphere_fitter, label) == f'{label} (2)'

    def test_snapshots_reset_when_model_changes(self, sphere_fitter, session_state):
        model_preview.add_snapshot(sphere_fitter)
        assert model_preview.get_snapshots(sphere_fitter)
        sphere_fitter.set_model('cylinder')
        assert model_preview.get_snapshots(sphere_fitter) == {}
        assert session_state[model_preview.SNAPSHOTS_RESET_KEY] is True

    def test_snapshots_reset_when_structure_factor_added(self, sphere_fitter, session_state):
        model_preview.add_snapshot(sphere_fitter)
        sphere_fitter.set_structure_factor('hardsphere')
        assert sphere_fitter.model_name == 'sphere'  # the name alone does not change
        assert model_preview.get_snapshots(sphere_fitter) == {}

    def test_snapshots_reset_when_structure_factor_removed(self, sphere_fitter, session_state):
        sphere_fitter.set_structure_factor('hardsphere')
        model_preview.add_snapshot(sphere_fitter, 'with SF')
        sphere_fitter.remove_structure_factor()
        snapshots = model_preview.get_snapshots(sphere_fitter)
        assert snapshots == {}
        # Nothing stale left to trip compare() on the removed SF parameters
        model_preview.add_snapshot(sphere_fitter)
        utils.plot_parameter_comparison(sphere_fitter, snapshots)

    def test_snapshots_reset_when_pd_distribution_changes(self, sphere_fitter, session_state):
        sphere_fitter.enable_polydispersity(True)
        model_preview.add_snapshot(sphere_fitter)
        sphere_fitter.set_pd_param('radius', pd_width=0.1)  # a width is a snapshot value
        assert model_preview.get_snapshots(sphere_fitter)
        sphere_fitter.set_pd_param('radius', pd_type='schulz')  # a type is not
        assert model_preview.get_snapshots(sphere_fitter) == {}

    def test_snapshots_survive_value_and_pd_toggle_changes(self, sphere_fitter, session_state):
        model_preview.add_snapshot(sphere_fitter)
        sphere_fitter.set_param('radius', value=30.0)
        sphere_fitter.enable_polydispersity(True)
        assert list(model_preview.get_snapshots(sphere_fitter)) == ['Snapshot 1']
        assert model_preview.SNAPSHOTS_RESET_KEY not in session_state


def test_preview_and_stale_fit_results_charts_render_together():
    """Both sections draw the same model_preview figure once a fit is stale."""
    from streamlit.testing.v1 import AppTest

    def app():
        import streamlit as st
        from sans_fitter import SANSFitter

        from sans_webapp.components.fit_results import render_fit_results
        from sans_webapp.components.model_preview import render_model_preview

        if 'fitter' not in st.session_state:
            fitter = SANSFitter()
            fitter.load_data('simulated_sans_data.csv')
            fitter.set_model('sphere')
            fitter.set_param('radius', value=40.0, min=5.0, max=200.0, vary=True)
            st.session_state.fit_result = fitter.fit(engine='bumps', method='amoeba')
            fitter.set_param('radius', value=30.0)
            st.session_state.fitter = fitter
            st.session_state.fit_completed = True
        render_model_preview(st.session_state.fitter)
        render_fit_results(st.session_state.fitter, {})

    at = AppTest.from_function(app, default_timeout=60).run()
    assert not at.exception
    assert [e.value for e in at.error] == []
    assert len(at.get('plotly_chart')) == 2
