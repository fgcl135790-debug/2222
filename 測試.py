import streamlit as st
from fugle_marketdata import WebSocketClient

st.write("WebSocketClient.stock")

st.write(dir(WebSocketClient.stock))

st.write("WebSocketClient.futopt")

st.write(dir(WebSocketClient.futopt))
