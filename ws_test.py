import streamlit as st
from fugle_marketdata import WebSocketClient
from fugle_marketdata.websocket.client import (
    MESSAGE_EVENT,
    AUTHENTICATED_EVENT,
    ERROR_EVENT
)

API_KEY = st.text_input("API KEY", type="password")

if API_KEY:

    ws = WebSocketClient(api_key=API_KEY)

    stock = ws.stock

    def on_auth(message):
        st.write("AUTH:", message)

    def on_message(message):
        st.write("MSG:", message)

    def on_error(error):
        st.write("ERROR:", error)

    stock.on(AUTHENTICATED_EVENT, on_auth)
    stock.on(MESSAGE_EVENT, on_message)
    stock.on(ERROR_EVENT, on_error)

    if st.button("Connect"):
        stock.connect()
        st.success("Connected")
