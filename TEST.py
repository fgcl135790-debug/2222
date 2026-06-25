import streamlit as st
from fugle_marketdata import WebSocketClient
import inspect

ws = WebSocketClient(api_key="TEST")
stock = ws.stock

st.text(inspect.getsource(stock.__class__))
