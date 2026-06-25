import streamlit as st
from fugle_marketdata.websocket.client import WebSocketClient
import inspect

st.text(inspect.getsource(WebSocketClient))
