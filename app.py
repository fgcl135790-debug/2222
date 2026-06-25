import streamlit as st
import pandas as pd

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from charts import ChartBuilder
from exporters import Exporter

st.set_page_config(
    page_title="REST PRO",
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

# =========================
# Data Provider
# =========================

try:

    if data_source == "真實盤":

        if not api_key:
            st.warning("請輸入 Fugle API Key")
            st.stop()

        provider = FugleProvider(api_key)

        quote = provider.get_quote(stock_code)

    else:

        engine = SimulationEngine(
            mode=sim_mode,
            base_price=100
        )

        quote = engine.generate(
            st.session_state.tick,
            sim_minutes * 60
        )

        st.session_state.tick += 1

except Exception as e:

    st.error(f"資料取得失敗：{e}")
    st.stop()

# =========================
# Quote
# =========================

name = quote["name"]

price = quote["price"]

vwap = quote["vwap"]

volume = quote["last_size"]

bids = quote["bids"]

asks = quote["asks"]

# =========================
# History
# =========================

st.session_state.price_history.append(price)

st.session_state.volume_history.append(volume)

st.session_state.price_history = (
    st.session_state.price_history[-500:]
)

st.session_state.volume_history = (
    st.session_state.volume_history[-500:]
)

prices = st.session_state.price_history

volumes = st.session_state.volume_history

# =========================
# Indicators
# =========================

ema5 = MarketAnalyzer.calculate_ema(
    prices,
    5
)

ema20 = MarketAnalyzer.calculate_ema(
    prices,
    20
)

ema60 = MarketAnalyzer.calculate_ema(
    prices,
    60
)

trend = MarketAnalyzer.trend(
    price,
    vwap,
    ema5,
    ema20
)

# =========================
# Header
# =========================

st.title(
    f"⚡ {name}"
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "現價",
    round(price, 2)
)

c2.metric(
    "VWAP",
    round(vwap, 2)
)

c3.metric(
    "EMA5",
    round(float(ema5), 2)
)

c4.metric(
    "趨勢",
    trend
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "EMA20",
    round(float(ema20), 2)
)

c2.metric(
    "EMA60",
    round(float(ema60), 2)
)

c3.metric(
    "成交量",
    volume
)

# =========================
# Chart
# =========================

st.subheader("📈 價格走勢")

fig = ChartBuilder.build_price_chart(
    prices,
    volumes
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =========================
# Best 5
# =========================

st.subheader("📋 最佳五檔")

while len(bids) < 5:
    bids.append({
        "price": 0,
        "size": 0
    })

while len(asks) < 5:
    asks.append({
        "price": 0,
        "size": 0
    })

df = pd.DataFrame({

    "買張":
        [x["size"] for x in bids[:5]],

    "買價":
        [x["price"] for x in bids[:5]],

    "賣價":
        [x["price"] for x in asks[:5]],

    "賣張":
        [x["size"] for x in asks[:5]],
})

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
)

# =========================
# Big Order Log
# =========================

if volume >= 100:

    st.session_state.big_order_log.insert(
        0,
        {
            "價格": price,
            "張數": volume,
            "來源": data_source
        }
    )

st.subheader("📜 大戶成交紀錄")

log_df = pd.DataFrame(
    st.session_state.big_order_log[:50]
)

st.dataframe(
    log_df,
    use_container_width=True,
    hide_index=True
)

# =========================
# Export
# =========================

csv_data = Exporter.export_big_order_log(
    st.session_state.big_order_log
)

st.download_button(
    "📥 下載成交紀錄",
    csv_data,
    file_name="big_order_log.csv",
    mime="text/csv"
)

st.caption("REST PRO v1")
