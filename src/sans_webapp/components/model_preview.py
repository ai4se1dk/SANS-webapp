"""
Model preview component for SANS webapp.

Shows the model at the current parameters against the data before (or
between) fits, and overlays saved parameter snapshots for comparison.
"""

import streamlit as st
from sans_fitter import SANSFitter

from sans_webapp.sans_analysis_utils import (
    CURRENT_PARAMETERS_LABEL,
    plot_model_preview,
    plot_parameter_comparison,
    snapshot_context,
    snapshot_parameters,
)
from sans_webapp.ui_constants import (
    CLEAR_SNAPSHOTS_BUTTON,
    LOG_SCALE_LABEL,
    MODEL_PREVIEW_CAPTION,
    MODEL_PREVIEW_HEADER,
    MODEL_PREVIEW_TAB_COMPARE,
    MODEL_PREVIEW_TAB_CURRENT,
    NO_SNAPSHOTS_INFO,
    SHOW_RESIDUALS_LABEL,
    SNAPSHOT_BUTTON,
    SNAPSHOT_DEFAULT_LABEL,
    SNAPSHOT_LABEL_INPUT,
    SNAPSHOT_LABEL_PLACEHOLDER,
    SNAPSHOTS_CAPTION,
    SNAPSHOTS_RESET_INFO,
)

SNAPSHOTS_KEY = 'param_snapshots'
SNAPSHOTS_RESET_KEY = 'param_snapshots_reset'


def get_snapshots(fitter: SANSFitter) -> dict[str, dict[str, float]]:
    """
    Return the parameter snapshots saved for the fitter's current configuration.

    Snapshots are keyed to ``snapshot_context()``: switching model, adding or
    removing a structure factor, changing links or polydispersity distribution
    settings discards them, since they could no longer be reproduced (or even
    evaluated) under the new configuration. A discard is recorded so the
    comparison tab can say why the snapshots are gone.
    """
    context = snapshot_context(fitter)
    stored = st.session_state.get(SNAPSHOTS_KEY)
    if not stored or stored.get('context') != context:
        if stored and stored.get('cases'):
            st.session_state[SNAPSHOTS_RESET_KEY] = True
        stored = {'context': context, 'cases': {}}
        st.session_state[SNAPSHOTS_KEY] = stored
    return stored['cases']


def add_snapshot(fitter: SANSFitter, label: str | None = None) -> str:
    """Save the current parameter values under *label* and return the label used."""
    snapshots = get_snapshots(fitter)
    base = (label or '').strip() or SNAPSHOT_DEFAULT_LABEL.format(n=len(snapshots) + 1)
    # The live curve's label is reserved in the comparison plot
    taken = set(snapshots) | {CURRENT_PARAMETERS_LABEL}
    unique = base
    suffix = 2
    while unique in taken:
        unique = f'{base} ({suffix})'
        suffix += 1
    snapshots[unique] = snapshot_parameters(fitter)
    return unique


def render_model_preview(fitter: SANSFitter) -> None:
    """
    Render the model preview section.

    Args:
        fitter: The SANSFitter instance with data and a model loaded
    """
    expanded = not st.session_state.get('fit_completed', False)
    with st.expander(MODEL_PREVIEW_HEADER, expanded=expanded):
        current_tab, compare_tab = st.tabs([MODEL_PREVIEW_TAB_CURRENT, MODEL_PREVIEW_TAB_COMPARE])

        with current_tab:
            _render_current_model(fitter)

        with compare_tab:
            _render_snapshot_comparison(fitter)


def _render_current_model(fitter: SANSFitter) -> None:
    st.caption(MODEL_PREVIEW_CAPTION)
    option_cols = st.columns(2)
    show_residuals = option_cols[0].checkbox(
        SHOW_RESIDUALS_LABEL, value=True, key='model_preview_residuals'
    )
    log_scale = option_cols[1].checkbox(LOG_SCALE_LABEL, value=True, key='model_preview_log_scale')
    try:
        fig = plot_model_preview(fitter, show_residuals=show_residuals, log_scale=log_scale)
        st.plotly_chart(fig, width='stretch', key='model_preview_chart')
    except Exception as e:
        st.error(f'Error plotting model preview: {str(e)}')


def _render_snapshot_comparison(fitter: SANSFitter) -> None:
    st.caption(SNAPSHOTS_CAPTION)
    snapshots = get_snapshots(fitter)
    if st.session_state.pop(SNAPSHOTS_RESET_KEY, False):
        st.info(SNAPSHOTS_RESET_INFO)

    def take_snapshot() -> None:
        # Runs before the rerun, so the label widget can still be reset here
        add_snapshot(fitter, st.session_state.get('snapshot_label'))
        st.session_state['snapshot_label'] = ''

    label_col, snap_col, clear_col = st.columns([2, 1, 1])
    label_col.text_input(
        SNAPSHOT_LABEL_INPUT, placeholder=SNAPSHOT_LABEL_PLACEHOLDER, key='snapshot_label'
    )
    snap_col.button(SNAPSHOT_BUTTON, on_click=take_snapshot)
    clear_col.button(CLEAR_SNAPSHOTS_BUTTON, on_click=snapshots.clear, disabled=not snapshots)

    if not snapshots:
        st.info(NO_SNAPSHOTS_INFO)
        return

    log_scale = st.checkbox(LOG_SCALE_LABEL, value=True, key='snapshot_log_scale')
    try:
        fig = plot_parameter_comparison(fitter, snapshots, log_scale=log_scale)
        st.plotly_chart(fig, width='stretch', key='snapshot_comparison_chart')
    except Exception as e:
        st.error(f'Error comparing parameter sets: {str(e)}')
