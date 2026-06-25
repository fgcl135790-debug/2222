import streamlit as st
from fugle_marketdata import WebSocketClient
import inspect

ws = WebSocketClient(api_key="TEST")
stock = ws.stock

st.write("subscribe")

st.code(str(inspect.signature(stock.subscribe)))

st.write("on")

st.code(str(inspect.signature(stock.on)))

st.write("connect")

st.code(str(inspect.signature(stock.connect)))
