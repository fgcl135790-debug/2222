import streamlit as st
from fugle_marketdata import WebSocketClient
from fugle_marketdata.websocket.client import (
    AUTHENTICATED_EVENT,
    ERROR_EVENT,
)

api_key = st.text_input("API KEY", type="password")

if api_key and st.button("Connect"):

    try:

        ws = WebSocketClient(api_key=api_key)

        stock = ws.stock

        def on_auth(msg):
            st.write("AUTH OK")
            st.json(msg)

        def on_error(err):
            st.write("ERROR EVENT")
            st.write(repr(err))

        stock.on(AUTHENTICATED_EVENT, on_auth)
        stock.on(ERROR_EVENT, on_error)

        stock.connect()

        st.success("Connected")

    except Exception as e:

        st.error(repr(e))
