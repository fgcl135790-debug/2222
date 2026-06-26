import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from charts import ChartBuilder
from streamlit_autorefresh import st_autorefresh


# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="準法人交易系統 V4",
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
# Time
# =========================
now = datetime.now(ZoneInfo("Asia/Taipei"))


# =========================
# Session State
# =========================
for k in ["price_history", "volume_history", "tick", "last_serial"]:
    if k not in st.session_state:
        st.session_state[k] = [] if "history" in k else 0


# =========================
# Sidebar
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

    auto_threshold = st.checkbox("自動大戶門檻", value=True)

    # 平均量計算
    avg_volume = 1
    suggest_threshold = 100

    if len(st.session_state.volume_history) > 0:
        avg_volume = sum(st.session_state.volume_history[-100:]) / max(len(st.session_state.volume_history[-100:]), 1)
        suggest_threshold = int(avg_volume * 3)

        st.info(f"平均量: {avg_volume:.0f}\n建議門檻: {suggest_threshold}")

    big_order_threshold = suggest_threshold if auto_threshold else st.number_input(
        "大戶門檻", 10, 10000, 100
    )

    sim_minutes = st.slider("模擬分鐘", 2, 60, 10)

    if st.button("重置"):
        st.session_state.price_history = []
        st.session_state.volume_history = []
        st.session_state.tick = 0
        st.session_state.last_serial = 0
        st.rerun()


# =========================
# Auto Refresh
# =========================
st_autorefresh(interval=refresh_sec * 1000, key="refresh")


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
    st.error(f"資料錯誤: {e}")
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
# History Fix（重點）
# =========================
if market_open and not is_close:
    if len(st.session_state.price_history) == 0 or trade_serial != st.session_state.last_serial:
        st.session_state.last_serial = trade_serial
        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)


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


# =========================
# AI Score
# =========================
ai_score = 50
reasons = []

if price > vwap:
    ai_score += 10
    reasons.append("站上VWAP")
else:
    ai_score -= 10

if ema5 > ema20 > ema60:
    ai_score += 20
    reasons.append("多頭排列")
elif ema5 < ema20 < ema60:
    ai_score -= 20
    reasons.append("空頭排列")

if rsi > 70:
    ai_score -= 10
elif rsi < 30:
    ai_score += 10

if macd > macd_signal:
    ai_score += 10
else:
    ai_score -= 10

if momentum > 0:
    ai_score += 5
else:
    ai_score -= 5

total_bid = sum(x["size"] for x in bids)
total_ask = sum(x["size"] for x in asks)

bid_ratio = total_bid / max(total_ask, 1)

if bid_ratio > 1.5:
    ai_score += 15
elif bid_ratio < 0.7:
    ai_score -= 15

ai_score = max(0, min(100, int(ai_score)))


# =========================
# 反轉區（完整修復）
# =========================
if ema5 > ema20 and rsi < 40:
    reversal = "BUY"
elif ema5 < ema20 and rsi > 60:
    reversal = "SELL"
else:
    reversal = "WATCH"


# =========================
# UI Header
# =========================
st.title(f"🏦 {name} ({stock_code})")

if is_close:
    st.error("已收盤")
else:
    st.success("即時更新")


# =========================
# Chart（修復你走勢圖）
# =========================
st.subheader("📈 走勢圖")
fig = ChartBuilder.build_price_chart(prices, volumes)
st.plotly_chart(fig, use_container_width=True)


# =========================
# 指標
# =========================
c1, c2, c3, c4 = st.columns(4)

c1.metric("現價", price)
c2.metric("VWAP", vwap)
c3.metric("EMA20", round(float(ema20), 2))
c4.metric("RSI", rsi)


# =========================
# AI 區
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("AI判斷")
    st.metric("分數", ai_score)
    st.progress(ai_score / 100)

with col2:
    st.subheader("反轉區")

    if reversal == "BUY":
        st.success("可能反彈")
    elif reversal == "SELL":
        st.error("可能轉弱")
    else:
        st.info("盤整")

with col3:
    st.subheader("理由")
    for r in reasons:
        st.write("•", r)


# =========================
# 五檔（完整修復）
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


# =========================
# Footer
# =========================
st.markdown("---")
st.caption("V4 完整法人級盤口系統")

