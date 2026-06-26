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
# Page Config
# =========================

st.set_page_config(
    page_title="準法人交易系統 V4.5",
    page_icon="🏦",
    layout="wide",
)

st.markdown("""
<style>
.block-container{
    padding:0.5rem 1rem;
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

for k in ["price_history", "volume_history", "big_order_log", "tick", "last_history_serial", "last_big_order_serial"]:
    if k not in st.session_state:
        st.session_state[k] = [] if "history" in k or "log" in k else 0


# =========================
# Sidebar
# =========================

with st.sidebar:

    st.title("⚙️ V4.5 控制中心")

    data_source = st.radio("資料來源", ["真實盤", "情境模擬"])

    stock_code = st.text_input("股票代號", "2330")

    api_key = st.text_input("Fugle API Key", type="password")

    sim_mode = st.selectbox(
        "模擬情境",
        ["一般波動", "軋空行情", "誘多出貨", "主力吸籌"]
    )

    refresh_sec = st.slider("更新秒數", 1, 10, 2)

    auto_threshold = st.checkbox("自動大戶門檻", value=True)


    # 平均量
    if len(st.session_state.volume_history) > 0:
        avg_volume = sum(st.session_state.volume_history[-100:]) / max(len(st.session_state.volume_history), 1)
        suggest_threshold = int(avg_volume * 3)

        st.info(f"平均量：{avg_volume:.0f}\n建議門檻：{suggest_threshold}")

    else:
        avg_volume = 1
        suggest_threshold = 100

    if auto_threshold:
        big_order_threshold = suggest_threshold
    else:
        big_order_threshold = st.number_input("大戶門檻", 10, 10000, 100)

    sim_minutes = st.slider("模擬分鐘", 2, 60, 10)

    if st.button("重置系統"):
        st.session_state.price_history = []
        st.session_state.volume_history = []
        st.session_state.big_order_log = []
        st.session_state.tick = 0
        st.session_state.last_history_serial = None
        st.session_state.last_big_order_serial = None
        st.rerun()


# =========================
# Auto Refresh
# =========================

st_autorefresh(interval=refresh_sec * 1000, key="v45_refresh")


# =========================
# Data Provider
# =========================

try:
    if data_source == "真實盤":

        if api_key == "":
            st.warning("請輸入 API Key")
            st.stop()

        provider = FugleProvider(api_key)
        quote = provider.get_quote(stock_code)

    else:
        engine = SimulationEngine(mode=sim_mode, base_price=100)
        quote = engine.generate(st.session_state.tick, sim_minutes * 60)
        st.session_state.tick += 1

except Exception as e:
    st.error(f"資料錯誤：{e}")
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
# Market Open
# =========================

market_open = (9 <= now.hour <= 13)


# =========================
# History
# =========================

if market_open and not is_close:

    if len(st.session_state.price_history) == 0 or trade_serial != st.session_state.last_history_serial:
        st.session_state.last_history_serial = trade_serial
        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)


st.session_state.price_history = st.session_state.price_history[-500:]
st.session_state.volume_history = st.session_state.volume_history[-500:]

prices = st.session_state.price_history
volumes = st.session_state.volume_history


# =========================
# Indicators
# =========================

ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)
ema60 = MarketAnalyzer.calculate_ema(prices, 60)

rsi = MarketAnalyzer.calculate_rsi(prices)
macd, macd_signal, macd_hist = MarketAnalyzer.calculate_macd(prices)

momentum = MarketAnalyzer.momentum(prices)
volatility = MarketAnalyzer.volatility(prices)
volume_trend = MarketAnalyzer.volume_trend(volumes)


total_bid = sum(x["size"] for x in bids)
total_ask = sum(x["size"] for x in asks)

bid_ratio = total_bid / max(total_ask, 1)


# =========================
# AI SCORE（法人版）
# =========================

ai_score = 50
reasons = []

if price > vwap:
    ai_score += 10
    reasons.append("站上VWAP（偏多）")
else:
    ai_score -= 10
    reasons.append("跌破VWAP（偏空）")

if ema5 > ema20 > ema60:
    ai_score += 20
    reasons.append("多頭排列")
elif ema5 < ema20 < ema60:
    ai_score -= 20
    reasons.append("空頭排列")

if rsi < 30:
    ai_score += 10
elif rsi > 70:
    ai_score -= 10

if macd > macd_signal:
    ai_score += 10
else:
    ai_score -= 10

if momentum > 0:
    ai_score += 5
else:
    ai_score -= 5

if bid_ratio > 1.5:
    ai_score += 15
elif bid_ratio < 0.7:
    ai_score -= 15

ai_score = max(0, min(100, int(ai_score)))


# =========================
# 反轉區（完整回來）
# =========================

if ema5 > ema20 and rsi < 40:
    reversal = "BUY"
elif ema5 < ema20 and rsi > 60:
    reversal = "SELL"
else:
    reversal = "WATCH"


# =========================
# HEADER
# =========================

st.title(f"🏦 {name} ({stock_code})")
st.caption(f"更新時間：{now.strftime('%Y-%m-%d %H:%M:%S')}")


# =========================
# 走勢圖（不會再消失）
# =========================

st.subheader("📈 法人走勢圖")

fig = ChartBuilder.build_price_chart(prices, volumes)
st.plotly_chart(fig, use_container_width=True)


# =========================
# 指標列
# =========================

c1, c2, c3, c4 = st.columns(4)

c1.metric("現價", price)
c2.metric("VWAP", vwap)
c3.metric("EMA20", round(float(ema20), 2))
c4.metric("RSI", rsi)


# =========================
# AI 判斷
# =========================

st.subheader("🤖 AI判斷")

st.progress(ai_score / 100)
st.write(f"分數：{ai_score}/100")

for r in reasons:
    st.write("•", r)


# =========================
# 反轉區 UI
# =========================

st.subheader("🔄 反轉區")

if reversal == "BUY":
    st.success("📈 可能反彈（法人回補）")
elif reversal == "SELL":
    st.error("📉 可能轉弱（法人出貨）")
else:
    st.info("⚪ 盤整（觀望）")


# =========================
# 五檔
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
