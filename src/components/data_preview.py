"""
Data preview component for SANS webapp.

Contains rendering functions for data visualization and statistics.
"""

import pandas as pd
import streamlit as st
from sans_fitter import SANSFitter

from sans_analysis_utils import plot_data_and_fit
from ui_constants import (
    DATA_PREVIEW_HEADER,
    DATA_STATS_HEADER,
    DATA_TABLE_HEIGHT,
    METRIC_DATA_POINTS,
    METRIC_MAX_INTENSITY,
    METRIC_Q_RANGE,
    SHOW_DATA_TABLE_LABEL,
)


def render_data_preview(fitter: SANSFitter) -> None:
    """
    Render the data preview section with plot and statistics.

    Args:
        fitter: The SANSFitter instance with loaded data
    """
    st.subheader(DATA_PREVIEW_HEADER)
    col1, col2 = st.columns([2, 1])

    with col1:
        # Plot data
        fig = plot_data_and_fit(fitter, show_fit=False)
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown(DATA_STATS_HEADER)
        data = fitter.data
        st.metric(METRIC_DATA_POINTS, len(data.x))
        st.metric(METRIC_Q_RANGE, f'{data.x.min():.4f} - {data.x.max():.4f} Å⁻¹')
        st.metric(METRIC_MAX_INTENSITY, f'{data.y.max():.4e} cm⁻¹')

        # Show data table
        if st.checkbox(SHOW_DATA_TABLE_LABEL):
            df = pd.DataFrame({'Q': data.x, 'I(Q)': data.y, 'dI(Q)': data.dy})
            st.dataframe(df.head(20), height=DATA_TABLE_HEIGHT)
