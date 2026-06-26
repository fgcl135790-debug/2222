import streamlit as st
import pandas as pd
import numpy as np

from datetime import datetime
from zoneinfo import ZoneInfo

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from ai_predictor import AIPredictor
from charts import ChartBuilder
from exporters import Exporter

from streamlit_autorefresh import st_autorefresh


# =========================
# V4.1 系統設定
# =========================

st.set_page_config(
    page_title="準法人交易系統 V4.1",
    page_icon="🏦",
    layout="wide",
)

st.markdown("""
<style>
.block-container{
    padding:0.6rem 1rem;
}
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
    "big_order_log": [],
    "last_serial": 0,
    "tick": 0
}

for k, v in default_state.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================
# Sidebar
# =========================

with st.sidebar:

    st.title("🏦 V4.1 控制中心")

    data_source = st.radio(
        "資料來源",
        ["真實盤", "情境模擬"]
    )

    stock_code = st.text_input("股票代號", "2330")

    api_key = st.text_input("Fugle API Key", type="password")

    sim_mode = st.selectbox(
        "模擬情境",
        ["一般波動", "軋空行情", "誘多出貨", "主力吸籌"]
    )

    refresh_sec = st.slider("更新秒數", 1, 10, 2)

    st.markdown("---")

# =========================
# Data Provider
# =========================

try:

    if data_source == "真實盤":

        if api_key == "":
            st.warning("請輸入 Fugle API Key")
            st.stop()

        provider = FugleProvider(api_key)
        quote = provider.get_quote(stock_code)

    else:

        engine = SimulationEngine(
            mode=sim_mode,
            base_price=100,
        )

        quote = engine.generate(
            st.session_state.tick,
            300,
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
volume = quote.get("last_size", 0)

bids = quote.get("bids", [])
asks = quote.get("asks", [])

trade = quote.get("trade", {})
trade_serial = trade.get("serial", 0)

is_close = quote.get("is_close", False)


# =========================
# Auto Refresh
# =========================

st_autorefresh(
    interval=refresh_sec * 1000,
    key="v4_refresh"
)


# =========================
# History（修復關鍵）
# =========================

if not is_close:

    if (
        len(st.session_state.price_history) == 0
        or trade_serial != st.session_state.last_serial
    ):

        st.session_state.last_serial = trade_serial
        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)

st.session_state.price_history = st.session_state.price_history[-300:]
st.session_state.volume_history = st.session_state.volume_history[-300:]

prices = st.session_state.price_history
volumes = st.session_state.volume_history

# =========================
# 五檔整理（V4.1 修復）
# =========================

def pad_book(book, is_bid=True):
    book = book.copy()
    while len(book) < 5:
        book.append({"price": 0, "size": 0})
    return book[:5]


bid5 = pad_book(bids, True)
ask5 = pad_book(asks, False)


# =========================
# 買賣盤統計
# =========================

total_bid = sum(x["size"] for x in bids)
total_ask = sum(x["size"] for x in asks)

bid_ratio = total_bid / max(total_ask, 1)

# =========================
# Header
# =========================

st.title(f"🏦 {name} ({stock_code})")
st.caption(f"更新時間：{now.strftime('%Y-%m-%d %H:%M:%S')}")

st.markdown("---")


# =========================
# 指標列
# =========================

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("現價", price)
c2.metric("VWAP", vwap)
c3.metric("EMA5", round(MarketAnalyzer.calculate_ema(prices, 5), 2))
c4.metric("EMA20", round(MarketAnalyzer.calculate_ema(prices, 20), 2))
c5.metric("RSI", round(MarketAnalyzer.calculate_rsi(prices), 2))
c6.metric("MACD", round(MarketAnalyzer.calculate_macd(prices)[0], 3))

st.markdown("---")


# =========================
# 五檔（UI補回）
# =========================

st.subheader("📊 五檔報價（法人盤口）")

col_b, col_a = st.columns(2)

with col_b:
    st.markdown("### 🔵 買盤")
    bid_df = pd.DataFrame(bid5)
    st.dataframe(bid_df, use_container_width=True, hide_index=True)

with col_a:
    st.markdown("### 🔴 賣盤")
    ask_df = pd.DataFrame(ask5)
    st.dataframe(ask_df, use_container_width=True, hide_index=True)

st.markdown("---")

# =========================
# AI（簡化顯示）
# =========================

ai_score = 50

if price > vwap:
    ai_score += 10
else:
    ai_score -= 10

ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)

if ema5 > ema20:
    ai_score += 10
else:
    ai_score -= 10

rsi = MarketAnalyzer.calculate_rsi(prices)

if rsi < 30:
    ai_score += 10
elif rsi > 70:
    ai_score -= 10

ai_score = max(0, min(int(ai_score), 100))


# =========================
# AI UI
# =========================

st.subheader("🧠 法人AI分析")

st.progress(ai_score / 100)
st.metric("AI分數", f"{ai_score}/100")

