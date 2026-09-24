"""
Data preview component for SANS webapp.

Contains rendering functions for data visualization and statistics.
"""

import numpy as np
import pandas as pd
import streamlit as st
from sans_fitter import SANSFitter

from sans_webapp.sans_analysis_utils import data_column_summary, plot_data
from sans_webapp.ui_constants import (
    DATA_PREVIEW_HEADER,
    DATA_STATS_HEADER,
    DATA_TABLE_HEIGHT,
    LOG_SCALE_LABEL,
    METRIC_DATA_POINTS,
    METRIC_FIT_Q_RANGE,
    METRIC_HAS_DI,
    METRIC_HAS_DQ,
    METRIC_MAX_INTENSITY,
    METRIC_NO,
    METRIC_Q_RANGE,
    METRIC_YES,
    SHOW_DATA_TABLE_LABEL,
    WARNING_NO_DI,
)


def render_data_preview(fitter: SANSFitter) -> None:
    """
    Render the data preview section with plot and statistics.

    Args:
        fitter: The SANSFitter instance with loaded data
    """
    expanded = st.session_state.get('expand_data_preview', True)
    with st.expander(DATA_PREVIEW_HEADER, expanded=expanded):
        col1, col2 = st.columns([2, 1])

        with col1:
            log_scale = st.checkbox(LOG_SCALE_LABEL, value=True, key='preview_log_scale')
            fig = plot_data(fitter, log_scale=log_scale)
            st.plotly_chart(fig, width='stretch', key='data_preview_chart')

        with col2:
            st.markdown(DATA_STATS_HEADER)
            data = fitter.data
            columns = data_column_summary(data)

            st.metric(METRIC_DATA_POINTS, len(data.x))
            st.metric(METRIC_Q_RANGE, f'{np.nanmin(data.x):.4f} - {np.nanmax(data.x):.4f} Å⁻¹')
            st.metric(METRIC_MAX_INTENSITY, f'{np.nanmax(data.y):.4e} cm⁻¹')

            # Optional columns: sasdata zero-fills absent dI/dQ, so ask sans-fitter
            # whether they carry real values rather than trusting their presence.
            flag_cols = st.columns(2)
            flag_cols[0].metric(METRIC_HAS_DI, METRIC_YES if columns['has_dy'] else METRIC_NO)
            flag_cols[1].metric(METRIC_HAS_DQ, METRIC_YES if columns['has_dx'] else METRIC_NO)
            if not columns['has_dy']:
                st.warning(WARNING_NO_DI)

            # Q range currently used for fitting (sans-fitter >= 0.4: set_q_range)
            q_range = fitter.get_q_range()
            if q_range is not None:
                st.metric(METRIC_FIT_Q_RANGE, f'{q_range[0]:.4g} - {q_range[1]:.4g} Å⁻¹')

            # Show data table
            if st.checkbox(SHOW_DATA_TABLE_LABEL):
                table = {'Q': data.x, 'I(Q)': data.y, 'dI(Q)': data.dy}
                if columns['has_dx']:
                    table['dQ'] = data.dx
                df = pd.DataFrame(table)
                st.dataframe(df.head(20), height=DATA_TABLE_HEIGHT)
