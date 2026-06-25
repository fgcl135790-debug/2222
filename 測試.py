import streamlit as st
import fugle_marketdata

st.title("Fugle Version Test")

st.write("Version:")

st.write(fugle_marketdata.__version__)
