import streamlit as st
from fugle_marketdata import WebSocketClient
import inspect

st.text(inspect.getsource(WebSocketClient))
