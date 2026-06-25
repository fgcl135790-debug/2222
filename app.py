import streamlit as st
import pandas as pd

from datetime import datetime

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from charts import ChartBuilder
from exporters import Exporter

# =========================
# Page Config
# =========================

st.set_page_config(
    page_title="REST PRO v2",
    page_icon="⚡",
    layout="wide",
)

# =========================
# Session State
# =========================

if "price_history" not in st.session_state:
    st.session_state.price_history = []

if "volume_history" not in st.session_state:
    st.session_state.volume_history = []

if "big_order_log" not in st.session_state:
    st.session_state.big_order_log = []

if "tick" not in st.session_state:
    st.session_state.tick = 0

# =========================
# Sidebar
# =========================

with st.sidebar:

    st.header("⚙️ 系統設定")

    data_source = st.radio(
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

    # =====================
    # 大戶門檻
    # =====================

    auto_threshold = st.checkbox(
        "自動大戶門檻",
        value=True
    )

    if len(st.session_state.volume_history) > 0:

        avg_volume = (
            sum(
                st.session_state.volume_history[-100:]
            )
            /
            min(
                len(st.session_state.volume_history),
                100
            )
        )

        suggest_threshold = int(
            avg_volume * 3
        )

        st.info(
            f"📊 最近100筆平均量：{avg_volume:.0f} 張\n\n"
            f"建議大戶門檻：{suggest_threshold} 張"
        )

    else:

        suggest_threshold = 100

    if auto_threshold:

        big_order_threshold = (
            suggest_threshold
        )

        st.success(
            f"目前使用自動門檻："
            f"{big_order_threshold} 張"
        )

    else:

        big_order_threshold = st.number_input(
            "大戶門檻(張)",
            min_value=10,
            max_value=10000,
            value=100,
            step=10
        )

    sim_minutes = st.slider(
        "模擬時間(分鐘)",
        2,
        60,
        10
    )

    if st.button("重置模擬"):

        st.session_state.price_history = []
        st.session_state.volume_history = []
        st.session_state.big_order_log = []
        st.session_state.tick = 0

        st.rerun()
