import streamlit as st
import pandas as pd
import numpy as np

from datetime import datetime
from zoneinfo import ZoneInfo

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from charts import ChartBuilder
from streamlit_autorefresh import st_autorefresh


# =========================
# 🏦 V5.5 券商級 UI
# =========================
st.set_page_config(
    page_title="V5.5 券商主力雷達",
    layout="wide"
)

st.markdown("""
<style>
html, body {font-size: 12px;}
.block-container {padding:0.4rem 0.6rem;}

.up {color:#ff3b3b;}   /* 台股紅 */
.down {color:#00c853;} /* 台股綠 */
</style>
""", unsafe_allow_html=True)


now = datetime.now(ZoneInfo("Asia/Taipei"))


# =========================
# Session State 修復
# =========================
for k in ["price_history", "volume_history", "tick", "last_serial", "current_stock"]:
    if k not in st.session_state:
        st.session_state[k] = [] if "history" in k else 0


def reset_state():
    st.session_state.price_history = []
    st.session_state.volume_history = []
    st.session_state.tick = 0
    st.session_state.last_serial = None


# =========================
# Sidebar
# =========================
with st.sidebar:

    st.title("⚙️ V5.5 主力雷達")

    source = st.radio("資料來源", ["真實盤", "情境模擬"])
    stock = st.text_input("股票代號", "2330")
    api_key = st.text_input("API Key", type="password")

    mode = st.selectbox("模擬模式", ["一般", "主力拉抬", "出貨", "洗盤"])

    refresh = st.slider("更新秒數", 1, 10, 2)

    if st.session_state.current_stock != stock:
        st.session_state.current_stock = stock
        reset_state()

    if st.button("重置"):
        reset_state()
        st.rerun()


st_autorefresh(interval=refresh * 1000, key="tick")


# =========================
# Data Source
# =========================
try:
    if source == "真實盤":
        provider = FugleProvider(api_key)
        quote = provider.get_quote(stock)
    else:
        engine = SimulationEngine(mode=mode, base_price=100)
        quote = engine.generate(st.session_state.tick, 600)
        st.session_state.tick += 1

except Exception as e:
    st.error(e)
    st.stop()


# =========================
# Quote 安全解析
# =========================
name = quote.get("name", "Unknown")
price = quote.get("price", 0)
vwap = quote.get("vwap", price)

bids = quote.get("bids") or []
asks = quote.get("asks") or []

volume = quote.get("last_size", 0)

trade = quote.get("trade", {})
serial = trade.get("serial", 0)


# =========================
# History 修復（換股會清）
# =========================
if st.session_state.last_serial != serial:
    st.session_state.last_serial = serial
    st.session_state.price_history.append(price)
    st.session_state.volume_history.append(volume)

st.session_state.price_history = st.session_state.price_history[-300:]
st.session_state.volume_history = st.session_state.volume_history[-300:]

prices = st.session_state.price_history
volumes = st.session_state.volume_history


# =========================
# 技術指標
# =========================
ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)
rsi = MarketAnalyzer.calculate_rsi(prices)
momentum = MarketAnalyzer.momentum(prices)


# =========================
# 📡 主力雷達（完整）
# =========================
bid_total = sum(x.get("size", 0) for x in bids)
ask_total = sum(x.get("size", 0) for x in asks)

buy_pressure = bid_total / max(bid_total + ask_total, 1)

big_order_flow = bid_total - ask_total

if big_order_flow > 500:
    smart_money = "🟢 大戶進場"
elif big_order_flow < -500:
    smart_money = "🔴 大戶出場"
else:
    smart_money = "🟡 中性"


main_score = (
    buy_pressure * 40 +
    (1 if ema5 > ema20 else -1) * 20 +
    momentum * 10 +
    (1 if price > vwap else -1) * 30
)

main_score = np.clip(main_score, 0, 100)


# =========================
# 🧠 AI語意（修復版）
# =========================
ai_score = 50
reasons = []

if price > vwap:
    ai_score += 10
    reasons.append("站上VWAP")
else:
    ai_score -= 10

if ema5 > ema20:
    ai_score += 15
else:
    ai_score -= 15

if rsi < 30:
    ai_score += 10
elif rsi > 70:
    ai_score -= 10

ai_score = np.clip(ai_score, 0, 100)


if ai_score >= 65:
    bias = "做多偏多"
elif ai_score <= 35:
    bias = "做空偏空"
else:
    bias = "盤整觀望"


# =========================
# 🔄 市場結構
# =========================
if ema5 < ema20 and rsi < 40:
    regime = "🔄 可能反彈區"
elif ema5 > ema20 and rsi > 60:
    regime = "📈 可能續漲"
else:
    regime = "📊 盤整區"


# =========================
# 📊 Chart
# =========================
st.title(f"🏦 V5.5 {name} ({stock})")

fig = ChartBuilder.build_price_chart(prices, volumes)
st.plotly_chart(fig, use_container_width=True)


# =========================
# 🧠 AI Panel（完整修復）
# =========================
st.subheader("🧠 AI 判讀")

col1, col2, col3 = st.columns(3)

col1.metric("市場傾向", bias)
col2.metric("AI信心", f"{int(ai_score)}%")
col3.metric("主力分數", int(main_score))

st.progress(ai_score / 100)

st.info(regime)


# =========================
# 📡 主力雷達 UI（補齊）
# =========================
st.subheader("📡 主力雷達")

st.write("大單流向：", smart_money)

st.metric("買壓", round(buy_pressure, 2))
st.metric("大單流", int(big_order_flow))

st.progress(main_score / 100)


# =========================
# 📋 五檔
# =========================
st.subheader("五檔")

while len(bids) < 5:
    bids.append({"price": 0, "size": 0})

while len(asks) < 5:
    asks.append({"price": 0, "size": 0})

st.dataframe(pd.DataFrame({
    "買價": [x["price"] for x in bids[:5]],
    "買量": [x["size"] for x in bids[:5]],
    "賣價": [x["price"] for x in asks[:5]],
    "賣量": [x["size"] for x in asks[:5]],
}))
