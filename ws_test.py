import streamlit as st
from fugle_marketdata import WebSocketClient
from fugle_marketdata.websocket.client import (
    MESSAGE_EVENT,
    AUTHENTICATED_EVENT,
    ERROR_EVENT
)

api_key = st.text_input("API KEY", type="password")

if api_key and st.button("Start"):

    ws = WebSocketClient(api_key=api_key)

    stock = ws.stock

    def on_auth(msg):
        st.write("AUTH")
        st.json(msg)

        try:
            stock.subscribe({
                "channel": "trades",
                "symbol": "2330"
            })
        except Exception as e:
            st.error(e)

    def on_message(msg):
        st.write("MESSAGE")
        st.code(msg)

    def on_error(err):
        st.write("ERROR")
        st.code(str(err))

    stock.on(AUTHENTICATED_EVENT, on_auth)
    stock.on(MESSAGE_EVENT, on_message)
    stock.on(ERROR_EVENT, on_error)

    stock.connect()

    st.success("Connected")
