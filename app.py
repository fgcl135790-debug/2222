import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime
from zoneinfo import ZoneInfo

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from ai_predictor import AIPredictor
from charts import ChartBuilder
from ui.header import render_header
from ui.ai_panel import render_ai_panel
from ui.orderbook import render_orderbook
from ui.radar import render_radar
from ui.chart_panel import render_chart
from streamlit_autorefresh import st_autorefresh
from ui.sidebar import render_sidebar


# =========================
# 🧠 V5.5 券商級設定
# =========================

st.set_page_config(
    page_title="主力監控",
    layout="wide",
    page_icon="🏦"
)

st.markdown("""
<style>
.block-container {
    padding: 0.4rem 0.8rem;
    font-size: 13px;
}

h1, h2, h3 {
    font-size: 16px !important;
}

.css-1d391kg {
    padding-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# =========================
# 🕒 台灣時間
# =========================
now = datetime.now(ZoneInfo("Asia/Taipei"))


# =========================
# 🧠 Session Reset（修復換股不清空）
# =========================
def reset_state():
    st.session_state.price_history = []
    st.session_state.volume_history = []
    st.session_state.tick = 0
    st.session_state.last_serial = None


for k in ["price_history", "volume_history", "tick", "last_serial"]:
    if k not in st.session_state:
        st.session_state[k] = [] if "history" in k else 0


# =========================
# 🧠 Sidebar
# =========================

(
    stock_code,
    data_source,
    api_key,
    mode,
    refresh_sec,
) = render_sidebar(reset_state)

# =========================
# ⏱ Auto refresh
# =========================
st_autorefresh(interval=refresh_sec * 1000, key="v55")


# =========================
# 📡 取得資料
# =========================
if data_source == "真實盤":
    if not api_key:
        st.warning("請輸入 API KEY")
        st.stop()

    provider = FugleProvider(api_key)
    quote = provider.get_quote(stock_code)

else:
    engine = SimulationEngine(mode="normal", base_price=100)
    quote = engine.generate(st.session_state.tick, 300)
    st.session_state.tick += 1


# =========================
# 📊 Quote解析
# =========================
name = quote.get("name", "Unknown")
price = quote["price"]
vwap = quote["vwap"]
volume = quote.get("last_size", 0)

bids = quote.get("bids", [])
asks = quote.get("asks", [])

trade = quote.get("trade", {})
serial = trade.get("serial", 0)


# =========================
# 🧠 換股自動清空（修復bug）
# =========================
if st.session_state.get("last_stock") != stock_code:
    reset_state()
    st.session_state.last_stock = stock_code


# =========================
# 📈 記錄價格
# =========================
if st.session_state.last_serial != serial:
    st.session_state.last_serial = serial
    st.session_state.price_history.append(price)
    st.session_state.volume_history.append(volume)

prices = st.session_state.price_history
volumes = st.session_state.volume_history


# =========================
# 📊 技術指標
# =========================
ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)
ema60 = MarketAnalyzer.calculate_ema(prices, 60)

rsi = MarketAnalyzer.calculate_rsi(prices)
macd, macd_signal, _ = MarketAnalyzer.calculate_macd(prices)

momentum = MarketAnalyzer.momentum(prices)


# =========================
# 🧠 AI Predict（V5.5）
# =========================
ai = AIPredictor.predict_trade(
    prices, volumes,
    ema5, ema20, ema60,
    rsi, macd, macd_signal,
    momentum,
    bid_ratio=1.2,
    vwap=vwap
)

signal = ai["signal"]
score = ai["score"]
risk = ai["risk"]
state = ai["market_state"]
rebound = ai["rebound_prob"]


# =========================
# 🧾 Header（券商級）
# =========================
render_header(
    name=name,
    stock_code=stock_code,
    price=price,
    score=score,
    risk=risk,
    state=state,
)


def signal_dot(color, text):
    return f"""
    <div style="
        display:flex;
        align-items:center;
        gap:8px;
        font-weight:600;
    ">
        <div style="
            width:12px;
            height:12px;
            border-radius:50%;
            background:{color};
            box-shadow:0 0 6px {color};
        "></div>
        <div>{text}</div>
    </div>
    """

# =========================
# 🧠 AI 判讀（V5.5 修正版）
# =========================

render_ai_panel(
    signal=signal,
    score=score,
    rebound=rebound,
)

# =========================
# 📡 主力雷達（台股正確顏色版）
# =========================

render_radar(
    bids=bids,
    asks=asks,
)

# =========================
# 📈 走勢圖
# =========================

render_chart(
    prices=prices,
    volumes=volumes,
)

# =========================
# 📋 五檔
# =========================

render_orderbook(
    bids=bids,
    asks=asks,
)
