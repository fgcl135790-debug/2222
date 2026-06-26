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
# ⚙️ Page Config（券商級）
# =========================
st.set_page_config(
    page_title="V4.6 券商系統",
    page_icon="🏦",
    layout="wide",
)

# 台股風格（紅漲綠跌）
st.markdown("""
<style>
.block-container {padding:0.4rem 0.8rem;}
html, body {font-size: 13px;}

.up {color:#ff3b3b;}
.down {color:#00c853;}

</style>
""", unsafe_allow_html=True)


# =========================
# Time
# =========================
now = datetime.now(ZoneInfo("Asia/Taipei"))


# =========================
# Session init（關鍵修復）
# =========================
def reset_stock():
    st.session_state.price_history = []
    st.session_state.volume_history = []
    st.session_state.tick = 0
    st.session_state.last_serial = None


if "current_stock" not in st.session_state:
    st.session_state.current_stock = None

if "price_history" not in st.session_state:
    st.session_state.price_history = []

if "volume_history" not in st.session_state:
    st.session_state.volume_history = []

if "tick" not in st.session_state:
    st.session_state.tick = 0

if "last_serial" not in st.session_state:
    st.session_state.last_serial = None


# =========================
# Sidebar
# =========================
with st.sidebar:

    st.title("⚙️ V4.6 券商中心")

    data_source = st.radio("資料來源", ["真實盤", "情境模擬"])
    stock_code = st.text_input("股票代號", "2330")
    api_key = st.text_input("Fugle API Key", type="password")

    sim_mode = st.selectbox("模擬", ["一般波動", "軋空行情", "誘空嘎空", "主力吸籌"])

    refresh_sec = st.slider("更新秒數", 1, 10, 2)

    # 換股 -> 清空（修復你UI錯亂主因）
    if st.session_state.current_stock != stock_code:
        st.session_state.current_stock = stock_code
        reset_stock()

    if st.button("重置系統"):
        reset_stock()
        st.rerun()


st_autorefresh(interval=refresh_sec * 1000, key="tick")


# =========================
# Data
# =========================
try:
    if data_source == "真實盤":
        provider = FugleProvider(api_key)
        quote = provider.get_quote(stock_code)
    else:
        engine = SimulationEngine(mode=sim_mode, base_price=100)
        quote = engine.generate(st.session_state.tick, 600)
        st.session_state.tick += 1

except Exception as e:
    st.error(e)
    st.stop()


# =========================
# Safe unpack（防爆）
# =========================
name = quote.get("name", stock_code)
price = quote.get("price", 0)
vwap = quote.get("vwap", price)

volume = quote.get("last_size", 0)
bids = quote.get("bids") or []
asks = quote.get("asks") or []

trade = quote.get("trade", {})
serial = trade.get("serial", 0)

is_close = quote.get("is_close", False)


# =========================
# Market session
# =========================
market_open = 9 <= now.hour <= 13


# =========================
# History（修復：不會亂掉）
# =========================
if market_open and not is_close:
    if st.session_state.last_serial != serial:
        st.session_state.last_serial = serial
        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)

st.session_state.price_history = st.session_state.price_history[-300:]
st.session_state.volume_history = st.session_state.volume_history[-300:]

prices = st.session_state.price_history
volumes = st.session_state.volume_history


# =========================
# Indicators
# =========================
ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)
rsi = MarketAnalyzer.calculate_rsi(prices)
macd, macd_signal, macd_hist = MarketAnalyzer.calculate_macd(prices)
momentum = MarketAnalyzer.momentum(prices)


# =========================
# Buy/Sell pressure
# =========================
total_bid = sum(x.get("size", 0) for x in bids)
total_ask = sum(x.get("size", 0) for x in asks)

buy_strength = total_bid / max(total_bid + total_ask, 1)


# =========================
# AI Signal（券商核心）
# =========================
if price > vwap:
    signal = "BUY"
elif price < vwap:
    signal = "SELL"
else:
    signal = "HOLD"


# =========================
# Reverse Zone（修復回來）
# =========================
if ema5 > ema20 and rsi < 40:
    reversal = "反彈區"
elif ema5 < ema20 and rsi > 60:
    reversal = "轉弱區"
else:
    reversal = "盤整"


# =========================
# Header
# =========================
st.title(f"🏦 {name} {stock_code}")

st.subheader("📈 法人走勢圖")

fig = ChartBuilder.build_price_chart(prices, volumes)
st.plotly_chart(fig, use_container_width=True)


# =========================
# Quote board
# =========================
c1, c2, c3, c4 = st.columns(4)

c1.metric("現價", price)
c2.metric("VWAP", round(vwap, 2))
c3.metric("EMA20", round(float(ema20), 2))
c4.metric("RSI", rsi)


# =========================
# AI panel
# =========================
st.subheader("🧠 AI 進出場訊號")

if signal == "BUY":
    st.success("🟢 多方進場")
elif signal == "SELL":
    st.error("🔴 空方出場")
else:
    st.info("⚪ 觀望")


st.write("🔄 反轉區：", reversal)


# =========================
# Radar（主力雷達）
# =========================
st.subheader("📡 主力雷達")

radar = buy_strength * 100

st.progress(radar / 100)
st.write(f"買盤強度：{radar:.1f}%")


# =========================
# Best5
# =========================
st.subheader("📋 五檔")

while len(bids) < 5:
    bids.append({"price": 0, "size": 0})

while len(asks) < 5:
    asks.append({"price": 0, "size": 0})

df = pd.DataFrame({
    "買價": [x["price"] for x in bids[:5]],
    "買量": [x["size"] for x in bids[:5]],
    "賣價": [x["price"] for x in asks[:5]],
    "賣量": [x["size"] for x in asks[:5]],
})

st.dataframe(df, use_container_width=True)
