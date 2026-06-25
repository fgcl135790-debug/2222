import streamlit as st
from fugle_marketdata import WebSocketClient

api_key = st.text_input("API KEY", type="password")

if api_key and st.button("Connect"):

    try:

        ws = WebSocketClient(api_key=api_key)

        stock = ws.stock

        stock.connect()

        st.success("Connected")

    except Exception as e:

        st.error(type(e).__name__)

        st.code(str(e))
