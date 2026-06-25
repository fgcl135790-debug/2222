import pkg_resources
import streamlit as st

st.write(
pkg_resources.get_distribution(
"fugle-marketdata"
).version
)
