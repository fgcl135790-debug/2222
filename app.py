import streamlit as st
import pandas as pd

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine

st.set_page_config(
    page_title="REST PRO",
    page_icon="⚡",
    layout="wide",
)

if "price_history" not in st.session_state:
    st.session_state.price_history = []

st.title("⚡ REST PRO 大戶監控")

with st.sidebar:

    mode = st.radio(
        "資料來源",
        [
            "真實盤",
            "情境模擬"
        ]
    )

    stock_code = st.text_input(
        "股票代號",
        "2330"
    )

    api_key = st.text_input(
        "Fugle API Key",
        type="password"
    )

    sim_mode = st.selectbox(
        "模擬情境",
        [
            "一般波動",
            "漲停鎖死",
            "跌停鎖死",
            "跳空急跌",
            "軋空行情",
            "誘多出貨",
            "誘空嘎空",
            "拉高出貨",
            "主力吸籌",
        ]
    )
