import streamlit as st
from fugle_marketdata import WebSocketClient
import inspect

ws = WebSocketClient(api_key="TEST")
stock = ws.stock

st.code(inspect.getsource(stock.subscribe))
