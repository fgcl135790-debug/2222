import streamlit as st
import sys
import fugle_marketdata

st.title("測試")

st.code(sys.version)

st.write(fugle_marketdata)

st.write(dir(fugle_marketdata))
