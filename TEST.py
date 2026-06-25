import streamlit as st
import pkg_resources

st.write(
    pkg_resources.get_distribution(
        "streamlit"
    ).version
)

st.write(
    pkg_resources.get_distribution(
        "plotly"
    ).version
)

st.write(
    pkg_resources.get_distribution(
        "fugle-marketdata"
    ).version
)
