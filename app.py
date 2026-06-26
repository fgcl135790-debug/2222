import streamlit as st
import pandas as pd
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
# V4.5 券商級 UI
# =========================

st.set_page_config(
    page_title="V4.5 券商中心",
    page_icon="🏦",
    layout="wide",
)

st.markdown("""
<style>
html, body, [class*="css"]  {
    font-size: 13px;
}

.block-container{
    padding:0.4rem 0.8rem;
}

/* 券商風格圖表 */
[data-testid="stPlotlyChart"]{
    height: 420px;
}

/* sidebar 縮小 */
section[data-testid="stSidebar"]{
    width: 280px;
}
</style>
""", unsafe_allow_html=True)


now = datetime.now(ZoneInfo("Asia/Taipei"))

if "last_stock" not in st.session_state:
    st.session_state.last_stock = None

def reset_state():
    st.session_state.price_history = []
    st.session_state.volume_history = []
    st.session_state.big_order_log = []
    st.session_state.tick = 0
    st.session_state.last_history_serial = None
    st.session_state.last_big_order_serial = None


for k in ["price_history","volume_history","big_order_log","tick",
          "last_history_serial","last_big_order_serial"]:
    if k not in st.session_state:
        if "history" in k or "log" in k:
            st.session_state[k] = []
        else:
            st.session_state[k] = 0
with st.sidebar:
    st.title("⚙️ V4.5 券商中心")

    data_source = st.radio("資料來源", ["真實盤", "情境模擬"])

    stock_code = st.text_input("股票代號", "2330")
    api_key = st.text_input("Fugle API Key", type="password")

    sim_mode = st.selectbox("模擬", ["一般波動","軋空行情","主力吸籌"])

    refresh_sec = st.slider("更新秒數", 1, 5, 2)

    auto_threshold = st.checkbox("自動大戶門檻", value=True)

    if st.button("重置系統"):
        reset_state()
        st.rerun()

st_autorefresh(interval=refresh_sec * 1000, key="v45")

if st.session_state.last_stock != stock_code:
    reset_state()
    st.session_state.last_stock = stock_code

if data_source == "真實盤":
    if not api_key:
        st.warning("請輸入 API Key")
        st.stop()

    provider = FugleProvider(api_key)
    quote = provider.get_quote(stock_code)

else:
    engine = SimulationEngine(mode=sim_mode, base_price=100)
    quote = engine.generate(st.session_state.tick, 600)
    st.session_state.tick += 1

name = quote.get("name", stock_code)
price = quote.get("price", 0)
vwap = quote.get("vwap", price)
volume = quote.get("last_size", 0)

bids = quote.get("bids", [])
asks = quote.get("asks", [])

trade = quote.get("trade", {})
serial = trade.get("serial", 0)

is_close = quote.get("is_close", False)

market_open = 9 <= now.hour <= 13

if market_open and not is_close:
    if len(st.session_state.price_history) == 0 or serial != st.session_state.last_history_serial:
        st.session_state.last_history_serial = serial
        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)

st.session_state.price_history = st.session_state.price_history[-300:]
st.session_state.volume_history = st.session_state.volume_history[-300:]

prices = st.session_state.price_history
volumes = st.session_state.volume_history

ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)
ema60 = MarketAnalyzer.calculate_ema(prices, 60)

rsi = MarketAnalyzer.calculate_rsi(prices)
macd, macd_signal, macd_hist = MarketAnalyzer.calculate_macd(prices)

momentum = MarketAnalyzer.momentum(prices)
volatility = MarketAnalyzer.volatility(prices)

total_bid = sum(x.get("size",0) for x in bids)
total_ask = sum(x.get("size",0) for x in asks)

bid_ratio = total_bid / max(total_ask, 1)

st.subheader("📈 法人走勢圖")

fig = ChartBuilder.build_price_chart(prices, volumes)

fig.update_layout(
    height=420,
    margin=dict(l=10, r=10, t=20, b=10),
)

st.plotly_chart(fig, use_container_width=True)
