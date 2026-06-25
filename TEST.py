import streamlit as st
import sys

st.write("Python:", sys.version)

try:
    import streamlit
    st.write("streamlit:", streamlit.__version__)
except Exception as e:
    st.write("streamlit error:", e)

try:
    import plotly
    st.write("plotly:", plotly.__version__)
except Exception as e:
    st.write("plotly error:", e)

try:
    import pandas
    st.write("pandas:", pandas.__version__)
except Exception as e:
    st.write("pandas error:", e)

try:
    import fugle_marketdata
    st.write("fugle-marketdata:", getattr(fugle_marketdata, "__version__", "unknown"))
except Exception as e:
    st.write("fugle-marketdata error:", e)
