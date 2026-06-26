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
# V4.5 券商級 UI
# =========================

st.set_page_config(
    page_title="V4.5 券商控制中心",
    page_icon="🏦",
    layout="wide",
)

st.markdown("""
<style>

/* ===== 全局縮小 ===== */
html, body {
    font-size: 13px;
}

.block-container {
    padding: 0.5rem 1rem;
}

/* 標題 */
h1 { font-size: 20px !important; }
h2 { font-size: 16px !important; }
h3 { font-size: 14px !important; }

/* metric */
[data-testid="metric-container"] {
    padding: 6px;
}

/* sidebar */
section[data-testid="stSidebar"] {
    font-size: 12px;
}

/* dataframe */
.dataframe {
    font-size: 11px;
}

/* button */
button {
    font-size: 12px !important;
}

</style>
""", unsafe_allow_html=True)


# =========================
# 台股顏色系統
# =========================

COLOR = {
    "UP": "#E53935",      # 紅 = 漲
    "DOWN": "#00C853",    # 綠 = 跌
    "FLAT": "#90A4AE",
}


# =========================
# 時間
# =========================

now = datetime.now(ZoneInfo("Asia/Taipei"))


# =========================
# Session State
# =========================

for k in ["price_history", "volume_history", "big_order_log", "tick", "last_serial"]:
    if k not in st.session_state:
        st.session_state[k] = [] if "history" in k or "log" in k else 0


# =========================
# Sidebar
# =========================

with st.sidebar:
    st.title("⚙️ V4.5 券商中心")

    data_source = st.radio("資料來源", ["真實盤", "情境模擬"])
    stock_code = st.text_input("股票代號", "2330")
    api_key = st.text_input("Fugle API Key", type="password")

    sim_mode = st.selectbox("模擬", ["一般", "軋空", "出貨", "吸籌"])

    refresh_sec = st.slider("更新秒數", 1, 10, 2)

    auto_threshold = st.checkbox("自動大戶門檻", True)

    sim_minutes = st.slider("模擬分鐘", 2, 60, 10)

    st_autorefresh(interval=refresh_sec * 1000, key="refresh")


# =========================
# Data Source
# =========================

if data_source == "真實盤":
    if not api_key:
        st.warning("請輸入API")
        st.stop()

    provider = FugleProvider(api_key)
    quote = provider.get_quote(stock_code)

else:
    engine = SimulationEngine(mode=sim_mode, base_price=100)
    quote = engine.generate(st.session_state.tick, sim_minutes * 60)
    st.session_state.tick += 1


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
serial = trade.get("serial", 0)

is_close = quote.get("is_close", False)

market_open = True


# =========================
# History
# =========================

if market_open and not is_close:
    if len(st.session_state.price_history) == 0 or serial != st.session_state.last_serial:
        st.session_state.last_serial = serial
        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)

prices = st.session_state.price_history[-300:]
volumes = st.session_state.volume_history[-300:]


# =========================
# 技術指標
# =========================

ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)
ema60 = MarketAnalyzer.calculate_ema(prices, 60)

rsi = MarketAnalyzer.calculate_rsi(prices)
macd, macd_signal, macd_hist = MarketAnalyzer.calculate_macd(prices)

momentum = MarketAnalyzer.momentum(prices)

bid = sum(x["size"] for x in bids)
ask = sum(x["size"] for x in asks)

bid_ratio = bid / max(ask, 1)


# =========================
# AI Score
# =========================

ai_score = 50
reasons = []

if price > vwap:
    ai_score += 10
    reasons.append("站上VWAP")

if ema5 > ema20:
    ai_score += 10
    reasons.append("短多格局")
else:
    ai_score -= 10
    reasons.append("短空格局")

if rsi > 70:
    ai_score -= 10
elif rsi < 30:
    ai_score += 10

if macd > macd_signal:
    ai_score += 10
else:
    ai_score -= 10

if bid_ratio > 1.5:
    ai_score += 15
elif bid_ratio < 0.7:
    ai_score -= 15

ai_score = max(0, min(100, ai_score))


# =========================
# 反轉區（券商版）
# =========================

if ema5 > ema20 and rsi < 40:
    reversal = "BUY"
elif ema5 < ema20 and rsi > 60:
    reversal = "SELL"
else:
    reversal = "WATCH"


# =========================
# Header
# =========================

st.title(f"🏦 {name} ({stock_code})")

if price > vwap:
    st.markdown(f"🔴 上漲趨勢")
else:
    st.markdown(f"🟢 下跌趨勢")


# =========================
# 走勢圖
# =========================

st.subheader("📈 走勢圖")

fig = ChartBuilder.build_price_chart(prices, volumes)
st.plotly_chart(fig, use_container_width=True)


# =========================
# 三大區塊（券商風格）
# =========================

c1, c2, c3 = st.columns(3)


# ===== AI判斷 =====
with c1:
    st.subheader("🤖 AI判斷")

    if ai_score > 70:
        st.markdown(f"🔴 偏多 {ai_score}")
    elif ai_score < 40:
        st.markdown(f"🟢 偏空 {ai_score}")
    else:
        st.markdown(f"⚪ 盤整 {ai_score}")

    st.progress(ai_score / 100)

    for r in reasons:
        st.write("•", r)


# ===== 反轉區 =====
with c2:
    st.subheader("🔄 反轉區")

    if reversal == "BUY":
        st.success("🔴 可能反彈")
    elif reversal == "SELL":
        st.error("🟢 可能轉弱")
    else:
        st.info("⚪ 盤整")

    st.metric("反轉機率", f"{50 + (ai_score-50)/2:.0f}%")


# ===== 技術面 =====
with c3:
    st.subheader("📊 技術面")

    st.metric("VWAP", round(vwap, 2))
    st.metric("EMA5", round(ema5, 2))
    st.metric("EMA20", round(ema20, 2))
    st.metric("RSI", int(rsi))


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

st.dataframe(df, use_container_width=True, hide_index=True)


# =========================
# Footer
# =========================

st.markdown("---")
st.caption("V4.5 券商級系統 | AI Flow Engine")
