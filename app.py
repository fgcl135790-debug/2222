import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from ai_predictor import AIPredictor
from charts import ChartBuilder

from streamlit_autorefresh import st_autorefresh


# =========================
# V5.5 券商級 UI
# =========================

st.set_page_config(
    page_title="V5.5 券商雷達系統",
    page_icon="🏦",
    layout="wide"
)

st.markdown("""
<style>
html, body, [class*="css"]  {
    font-size: 13px;
}

.block-container {
    padding: 0.5rem 0.8rem;
}

h1, h2, h3 {
    font-size: 16px !important;
}

/* 台股紅漲綠跌 */
.up { color: #ff4d4f; }
.down { color: #2ecc71; }

</style>
""", unsafe_allow_html=True)


# =========================
# 台灣時間
# =========================

now = datetime.now(ZoneInfo("Asia/Taipei"))


# =========================
# Session State
# =========================

default_state = {
    "price_history": [],
    "volume_history": [],
    "tick": 0,
    "last_serial": None,
    "stock_code": None
}

for k, v in default_state.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =========================
# Sidebar（券商級控制中心）
# =========================

with st.sidebar:

    st.title("⚙️ V5.5 券商雷達")

    data_source = st.radio("資料來源", ["真實盤", "情境模擬"])
    stock_code = st.text_input("股票代號", "2330")

    api_key = st.text_input("Fugle API Key", type="password")

    sim_mode = st.selectbox(
        "模擬模式",
        ["一般波動", "軋空", "出貨", "吸籌"]
    )

    refresh_sec = st.slider("刷新秒數", 1, 5, 2)

    if st.button("重置系統"):
        st.session_state.price_history = []
        st.session_state.volume_history = []
        st.session_state.tick = 0
        st.session_state.last_serial = None
        st.rerun()

st_autorefresh(interval=refresh_sec * 1000, key="refresh")
