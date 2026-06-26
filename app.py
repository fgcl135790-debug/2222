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
# V4 SYSTEM
# =========================

st.set_page_config(
    page_title="準法人交易系統 V4.1 AI PRO",
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
# TIME
# =========================

now = datetime.now(ZoneInfo("Asia/Taipei"))


# =========================
# SESSION STATE FIX
# =========================

def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default


init_state("price_history", [])
init_state("volume_history", [])
init_state("big_order_log", [])
init_state("tick", 0)
init_state("last_serial", 0)
init_state("last_big_serial", 0)


# =========================
# SIDEBAR
# =========================

with st.sidebar:

    st.title("⚙️ V4 控制中心")

    data_source = st.radio("資料來源", ["真實盤", "情境模擬"])

    stock_code = st.text_input("股票代號", "2330")

    api_key = st.text_input("Fugle API Key", type="password")

    sim_mode = st.selectbox(
        "模擬情境",
        ["一般波動", "軋空行情", "誘多出貨", "主力吸籌"]
    )

    refresh_sec = st.slider("更新秒數", 1, 10, 2)


# =========================
# DATA PROVIDER
# =========================

try:

    if data_source == "真實盤":

        if api_key == "":
            st.warning("請輸入 API KEY")
            st.stop()

        provider = FugleProvider(api_key)
        quote = provider.get_quote(stock_code)

    else:

        engine = SimulationEngine(mode=sim_mode, base_price=100)

        quote = engine.generate(
            st.session_state.tick,
            300
        )

        st.session_state.tick += 1

except Exception as e:
    st.error(f"資料錯誤: {e}")
    st.stop()


# =========================
# QUOTE
# =========================

name = quote["name"]
price = quote["price"]
vwap = quote["vwap"]
volume = quote.get("last_size", 0)

bids = quote.get("bids", [])
asks = quote.get("asks", [])

trade = quote.get("trade", {})
serial = trade.get("serial", 0)

is_close = quote.get("is_close", False)


# =========================
# AUTO REFRESH
# =========================

st_autorefresh(interval=refresh_sec * 1000, key="refresh")


# =========================
# HISTORY FIX（關鍵）
# =========================

if not is_close:

    if serial != st.session_state.last_serial:

        st.session_state.last_serial = serial

        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)


# limit
st.session_state.price_history = st.session_state.price_history[-300:]
st.session_state.volume_history = st.session_state.volume_history[-300:]

prices = st.session_state.price_history
volumes = st.session_state.volume_history


# =========================
# TECH
# =========================

ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)
ema60 = MarketAnalyzer.calculate_ema(prices, 60)

rsi = MarketAnalyzer.calculate_rsi(prices)
macd, macd_signal, macd_hist = MarketAnalyzer.calculate_macd(prices)

momentum = MarketAnalyzer.momentum(prices)
volatility = MarketAnalyzer.volatility(prices)
volume_trend = MarketAnalyzer.volume_trend(volumes)


# =========================
# BUY SELL DEPTH
# =========================

total_bid = sum(x["size"] for x in bids)
total_ask = sum(x["size"] for x in asks)

bid_ratio = total_bid / max(total_ask, 1)


# =========================
# AI SCORE V4
# =========================

ai_score = 50
reasons = []

if ema5 > ema20 > ema60:
    ai_score += 20
    reasons.append("多頭排列")

elif ema5 < ema20 < ema60:
    ai_score -= 20
    reasons.append("空頭排列")

if price > vwap:
    ai_score += 10
    reasons.append("站上VWAP")
else:
    ai_score -= 10

if rsi > 70:
    ai_score -= 10
elif rsi < 30:
    ai_score += 10

if macd > macd_signal:
    ai_score += 10
else:
    ai_score -= 10

if bid_ratio > 1.5:
    ai_score += 10
elif bid_ratio < 0.7:
    ai_score -= 10

ai_score = max(0, min(ai_score, 100))


# =========================
# HEADER
# =========================

st.title(f"🏦 {name} ({stock_code})")
st.caption(f"更新時間: {now}")


if is_close:
    st.warning("已收盤")
else:
    st.success("即時更新")


# =========================
# 📈 走勢圖（修復）
# =========================

st.subheader("📈 即時走勢")

fig = ChartBuilder.build_price_chart(prices, volumes)

st.plotly_chart(fig, use_container_width=True)


# =========================
# INDICATORS
# =========================

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("現價", price)
c2.metric("VWAP", vwap)
c3.metric("EMA5", round(float(ema5), 2))
c4.metric("EMA20", round(float(ema20), 2))
c5.metric("RSI", rsi)
c6.metric("MACD", round(macd, 4))


st.markdown("---")


# =========================
# AI PANEL
# =========================

col1, col2, col3 = st.columns(3)


with col1:

    st.subheader("🤖 AI判斷")

    if ai_score >= 70:
        st.success(f"偏多 {ai_score}%")
    elif ai_score <= 40:
        st.error(f"偏空 {ai_score}%")
    else:
        st.warning(f"中性 {ai_score}%")

    st.progress(ai_score / 100)

    for r in reasons:
        st.write("•", r)


# =========================
# 5 LEVEL DEPTH（修復五檔）
# =========================

with col2:

    st.subheader("📊 五檔")

    bids = (bids + [{"price": 0, "size": 0}] * 5)[:5]
    asks = (asks + [{"price": 0, "size": 0}] * 5)[:5]

    df = pd.DataFrame({
        "買價": [x["price"] for x in bids],
        "買量": [x["size"] for x in bids],
        "賣價": [x["price"] for x in asks],
        "賣量": [x["size"] for x in asks],
    })

    st.dataframe(df, use_container_width=True, hide_index=True)


# =========================
# FLOW
# =========================

with col3:

    st.subheader("🏦 主力")

    st.metric("買壓", total_bid)
    st.metric("賣壓", total_ask)
    st.metric("比例", round(bid_ratio, 2))


    if bid_ratio > 1.5:
        st.success("主力偏多")
    elif bid_ratio < 0.7:
        st.error("主力出貨")
    else:
        st.info("中性")


# =========================
# BIG ORDER LOG
# =========================

st.markdown("---")
st.subheader("📜 大戶成交")

if volume >= 800 and serial != st.session_state.last_big_serial:

    st.session_state.last_big_serial = serial

    st.session_state.big_order_log.insert(0, {
        "時間": now.strftime("%H:%M:%S"),
        "價格": price,
        "量": volume,
        "AI": ai_score
    })

df_log = pd.DataFrame(st.session_state.big_order_log)

st.dataframe(df_log, use_container_width=True, hide_index=True)


# =========================
# FOOTER
# =========================

st.markdown("---")
st.caption("V4.1 FIXED FULL SYSTEM")
