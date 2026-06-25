import streamlit as st
from fugle_marketdata import RestClient

st.title("Fugle Test")

api_key = st.text_input("API Key")

if api_key:
    try:
        client = RestClient(api_key=api_key)

        quote = client.stock.intraday.quote(symbol="2330")

        st.write(quote)

    except Exception as e:
        st.exception(e)
