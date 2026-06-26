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
# V4 系統設定
# =========================

st.set_page_config(
    page_title="準法人交易系統 V4",
    page_icon="🏦",
    layout="wide",
)

# UI優化
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

for k in [
    "price_history",
    "volume_history",
    "big_order_log",
    "last_serial",
    "tick"
]:
    if k not in st.session_state:
        st.session_state[k] = [] if "history" in k or "log" in k else 0

# =========================
# Sidebar
# =========================

with st.sidebar:

    st.title("⚙️ V4 控制中心")

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
# Quote 解包（V4強化版）
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

market_open = (
    (now.hour > 9 or (now.hour == 9 and now.minute >= 0))
    and
    (now.hour < 13 or (now.hour == 13 and now.minute <= 30))
)


# =========================
# Auto Refresh
# =========================

st_autorefresh(
    interval=refresh_sec * 1000,
    key="v4_refresh"
)


# =========================
# History 修復（關鍵！避免不動）
# =========================

if market_open and not is_close:

    if (
        len(st.session_state.price_history) == 0
        or trade_serial != st.session_state.last_serial
    ):

        st.session_state.last_serial = trade_serial

        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)


# 保留長度
st.session_state.price_history = st.session_state.price_history[-300:]
st.session_state.volume_history = st.session_state.volume_history[-300:]


prices = st.session_state.price_history
volumes = st.session_state.volume_history

# =========================
# 技術指標
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
# 買賣盤（法人版）
# =========================

total_bid = sum(x["size"] for x in bids)
total_ask = sum(x["size"] for x in asks)

bid_ratio = total_bid / max(total_ask, 1)


# =========================
# 🧠 V4 法人 AI（重點）
# =========================

ai_score = 50
reasons = []

# ===== 趨勢濾波（降低敏感度）=====
trend_filter = (ema20 - ema60)

if abs(trend_filter) < price * 0.001:
    ai_score += 0   # 橫盤不亂動
else:
    ai_score += 10 if trend_filter > 0 else -10

# ===== VWAP =====
if price > vwap:
    ai_score += 10
    reasons.append("站上VWAP（法人偏多）")
else:
    ai_score -= 10
    reasons.append("跌破VWAP（法人偏空）")

# ===== 均線結構（法人核心）=====
if ema5 > ema20 > ema60:
    ai_score += 20
    reasons.append("多頭排列（法人進場）")

elif ema5 < ema20 < ema60:
    ai_score -= 20
    reasons.append("空頭排列（法人出貨）")

# ===== RSI（避免過度敏感）=====
if 40 <= rsi <= 60:
    ai_score += 5
    reasons.append("RSI中性區（穩定）")

elif rsi > 75:
    ai_score -= 10
    reasons.append("RSI過熱（追高風險）")

elif rsi < 30:
    ai_score += 10
    reasons.append("RSI超賣（法人撿便宜）")

# ===== MACD（趨勢確認）=====
if macd > macd_signal:
    ai_score += 10
    reasons.append("MACD多頭")
else:
    ai_score -= 10
    reasons.append("MACD空頭")

# ===== 成交量（法人動能）=====
if volume_trend == "UP":
    ai_score += 10
    reasons.append("量能放大（法人進場）")
elif volume_trend == "DOWN":
    ai_score -= 10
    reasons.append("量能萎縮")

# ===== 委買委賣（主力）=====
if bid_ratio > 2:
    ai_score += 15
    reasons.append("強力吃單（主力買）")

elif bid_ratio > 1.3:
    ai_score += 8
    reasons.append("買盤偏強")

elif bid_ratio < 0.7:
    ai_score -= 15
    reasons.append("賣壓沉重（出貨）")

# ===== 波動過濾（降低亂跳）=====
if volatility > 3:
    ai_score -= 5
elif volatility < 0.5:
    ai_score -= 5

# =========================
# 限制範圍
# =========================

ai_score = max(0, min(int(ai_score), 100))


# =========================
# V4 分級（法人版）
# =========================

if ai_score >= 80:
    action = "🔥 法人強力做多"

elif ai_score >= 65:
    action = "📈 偏多（法人進場）"

elif ai_score >= 50:
    action = "⚪ 盤整（觀望）"

elif ai_score >= 35:
    action = "📉 偏空（法人減碼）"

else:
    action = "💥 強力出貨"


confidence = ai_score

with col1:

    st.subheader("🤖 AI交易判斷")

    if action.startswith("🔥"):
        st.success(f"🟢 {action}　{confidence}%")

    elif "偏多" in action:
        st.info(f"📈 {action}　{confidence}%")

    elif "偏空" in action:
        st.warning(f"📉 {action}　{confidence}%")

    elif "出貨" in action:
        st.error(f"🔴 {action}　{confidence}%")

    else:
        st.warning(f"⚪ {action}　{confidence}%")

    st.progress(confidence / 100)

    st.markdown("#### AI理由")
    for r in reasons:
        st.write("•", r)
