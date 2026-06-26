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
    page_title="REST PRO v3",
    page_icon="📈",
    layout="wide",
)

st.markdown("""
<style>
.block-container{
    padding-top:0.5rem;
    padding-bottom:0.5rem;
    padding-left:1rem;
    padding-right:1rem;
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

if "price_history" not in st.session_state:
    st.session_state.price_history = []

if "volume_history" not in st.session_state:
    st.session_state.volume_history = []

if "big_order_log" not in st.session_state:
    st.session_state.big_order_log = []

if "last_history_serial" not in st.session_state:
    st.session_state.last_history_serial = None

if "last_big_order_serial" not in st.session_state:
    st.session_state.last_big_order_serial = None

if "tick" not in st.session_state:
    st.session_state.tick = 0


# =========================
# Sidebar
# =========================

with st.sidebar:

    st.header("⚙️ 系統設定")

    data_source = st.radio(
        "資料來源",
        ["真實盤", "情境模擬"],
    )

    stock_code = st.text_input(
        "股票代號",
        "2330",
    )

    api_key = st.text_input(
        "Fugle API Key",
        type="password",
    )

    sim_mode = st.selectbox(
        "模擬情境",
        [
            "一般波動",
            "漲停鎖死",
            "跌停鎖死",
            "跳空急跌",
            "軋空行情",
            "誘多出貨",
            "誘空嘎空",
            "拉高出貨",
            "主力吸籌",
        ],
    )

    # =========================
    # 更新秒數
    # =========================

    refresh_sec = st.slider(
        "更新秒數",
        min_value=1,
        max_value=30,
        value=2,
        step=1,
    )


    # =========================
    # 大戶門檻
    # =========================

    auto_threshold = st.checkbox(
        "自動大戶門檻",
        value=True,
    )

    sim_minutes = st.slider(
        "模擬分鐘",
        2,
        60,
        10,
    )

    if st.button("重置模擬"):

        st.session_state.price_history = []
        st.session_state.volume_history = []
        st.session_state.big_order_log = []
        st.session_state.last_history_serial = None
        st.session_state.last_big_order_serial = None
        st.session_state.tick = 0

        st.rerun()


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
            sim_minutes * 60,
        )

        st.session_state.tick += 1

except Exception as e:

    st.error(f"資料取得失敗：{e}")
    st.stop()


# =========================
# Quote 拆解
# =========================

name = quote["name"]
price = quote["price"]
vwap = quote["vwap"]
volume = quote["last_size"]
bids = quote["bids"]
asks = quote["asks"]

trade = quote["trade"]
trade_serial = trade.get("serial", 0)

is_close = quote.get("is_close", False)


# =========================
# 市場時間
# =========================

market_open = (
    (
        now.hour > 9 or (now.hour == 9 and now.minute >= 0)
    )
    and
    (
        now.hour < 13 or (now.hour == 13 and now.minute <= 30)
    )
)


# =========================
# Auto Refresh
# =========================

st_autorefresh(
    interval=refresh_sec * 1000,
    key="refresh",
)


if is_close:

    st.sidebar.warning("🔴 已收盤")

else:

    st.sidebar.success("🟢 即時更新中")


# =========================
# History 更新
# =========================

if market_open and not is_close:

    if (
        len(st.session_state.price_history) == 0
        or trade_serial != st.session_state.last_history_serial
    ):

        st.session_state.last_history_serial = trade_serial

        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)


st.session_state.price_history = st.session_state.price_history[-500:]
st.session_state.volume_history = st.session_state.volume_history[-500:]

prices = st.session_state.price_history
volumes = st.session_state.volume_history


# =========================
# 技術指標
# =========================

ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)
ema60 = MarketAnalyzer.calculate_ema(prices, 60)

sma20 = MarketAnalyzer.calculate_sma(prices, 20)

trend = MarketAnalyzer.trend(price, vwap, ema5, ema20)

momentum = MarketAnalyzer.momentum(prices)
volatility = MarketAnalyzer.volatility(prices)
rsi = MarketAnalyzer.calculate_rsi(prices)

macd, macd_signal, macd_hist = MarketAnalyzer.calculate_macd(prices)

volume_trend = MarketAnalyzer.volume_trend(volumes)


# =========================
# 買賣盤
# =========================

total_bid = sum(x["size"] for x in bids)
total_ask = sum(x["size"] for x in asks)

buy_strength = round(
    total_bid / max(total_bid + total_ask, 1) * 100
)

sell_strength = 100 - buy_strength


# =========================
# AI 分析
# =========================

action, confidence, reasons = AIPredictor.score(
    price=price,
    vwap=vwap,
    ema5=ema5,
    ema20=ema20,
    ema60=ema60,
    rsi=rsi,
    macd=macd,
    macd_signal=macd_signal,
    macd_hist=macd_hist,
    total_bid=total_bid,
    total_ask=total_ask,
    momentum=momentum,
    volume_trend=volume_trend,
    volatility=volatility,
)

(
    reversal_signal,
    reversal_text,
    reversal_probability,
    reversal_stars,
    reversal_reasons,
) = AIPredictor.predict_reversal(
    price=price,
    prices=prices,
    vwap=vwap,
    ema5=ema5,
    ema20=ema20,
    ema60=ema60,
    rsi=rsi,
    macd=macd,
    macd_signal=macd_signal,
    total_bid=total_bid,
    total_ask=total_ask,
    momentum=momentum,
)


# =========================
# Header
# =========================

if is_close:
    st.warning("🔴 已收盤")
else:
    st.success("🟢 即時更新中")

st.title(f"⚡ {name} ({stock_code})")
st.caption(f"更新時間：{now.strftime('%Y-%m-%d %H:%M:%S')}")


# =========================
# Chart
# =========================

st.subheader("📈 即時走勢")

fig = ChartBuilder.build_price_chart(prices, volumes)

st.plotly_chart(fig, use_container_width=True)


# =========================
# 指標列
# =========================

st.markdown("---")

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("現價", round(price, 2))
c2.metric("VWAP", round(vwap, 2))
c3.metric("EMA5", round(float(ema5), 2))
c4.metric("EMA20", round(float(ema20), 2))
c5.metric("RSI", rsi)
c6.metric("MACD", macd)


# =========================
# AI 區塊
# =========================

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

# =========================
# 五檔報價
# =========================

st.subheader("📋 最佳五檔")

bid_list = bids.copy()
ask_list = asks.copy()

while len(bid_list) < 5:
    bid_list.append({"price": 0, "size": 0})

while len(ask_list) < 5:
    ask_list.append({"price": 0, "size": 0})

best5_df = pd.DataFrame({

    "買張": [x["size"] for x in bid_list[:5]],
    "買價": [x["price"] for x in bid_list[:5]],

    "賣價": [x["price"] for x in ask_list[:5]],
    "賣張": [x["size"] for x in ask_list[:5]],
})

st.dataframe(
    best5_df,
    use_container_width=True,
    hide_index=True,
    height=220,
)

# =========================
# AI交易判斷
# =========================

with col1:

    st.subheader("🤖 AI交易判斷")

    if action in ["STRONG BUY", "BUY"]:
        st.success(f"📈 {action}　{confidence}%")

    elif action in ["STRONG SELL", "SELL"]:
        st.error(f"📉 {action}　{confidence}%")

    else:
        st.warning(f"⚪ {action}　{confidence}%")

    st.progress(confidence / 100)

    st.markdown("#### AI分析")

    for r in reasons:
        st.write("•", r)


# =========================
# AI反轉預測（台股顏色修正）
# =========================

with col2:

    st.subheader("🔄 AI反轉預測")

    if reversal_signal == "BUY":
        st.success(reversal_text)   # 🔴上漲用紅色/綠色依你偏好可調

    elif reversal_signal == "SELL":
        st.error(reversal_text)     # 🔴下跌（紅色）

    elif reversal_signal == "WATCH":
        st.warning(reversal_text)

    else:
        st.info(reversal_text)

    st.metric("AI信心", f"{reversal_probability}%")
    st.progress(reversal_probability / 100)

    st.write(reversal_stars)

    st.markdown("#### AI依據")

    for r in reversal_reasons:
        st.write("•", r)


# =========================
# 技術分析
# =========================

with col3:

    st.subheader("📊 技術分析")

    st.metric("Momentum", round(momentum, 2))
    st.metric("RSI", rsi)
    st.metric("MACD", macd)
    st.metric("波動率", volatility)
    st.metric("成交量趨勢", volume_trend)
    st.metric("SMA20", round(float(sma20), 2))
    st.metric("MACD Hist", round(macd_hist, 3))


# =========================
# 主力分析
# =========================

with col4:

    st.subheader("🏦 主力分析")

    st.metric("委買", total_bid)
    st.metric("委賣", total_ask)
    st.metric("買盤比例", f"{buy_strength}%")

    bid_ratio = total_bid / max(total_ask, 1)

    if bid_ratio >= 2:
        st.success("🔴 強力買盤")
    elif bid_ratio >= 1.3:
        st.info("📈 偏多")
    elif bid_ratio <= 0.5:
        st.error("🟢 強力賣盤")
    else:
        st.warning("⚪ 中性")


# =========================
# 漲停機率（穩定版）
# =========================

limit_score = 5

if price > vwap:
    limit_score += 15

if ema5 > ema20:
    limit_score += 15

if ema20 > ema60:
    limit_score += 10

if bid_ratio >= 2:
    limit_score += 20
elif bid_ratio >= 1.5:
    limit_score += 15
elif bid_ratio >= 1.2:
    limit_score += 8

if momentum >= 3:
    limit_score += 15
elif momentum >= 1:
    limit_score += 8

if 55 <= rsi <= 70:
    limit_score += 10
elif rsi > 75:
    limit_score -= 10

if macd > macd_signal:
    limit_score += 10

if volume_trend == "UP":
    limit_score += 10

limit_score = max(0, min(int(limit_score), 100))


st.metric("🚀 漲停機率", f"{limit_score}%")
st.progress(limit_score / 100)

st.markdown("---")


# =========================
# Footer
# =========================

st.caption("REST PRO v3 | AI Order Flow Analyzer")
st.caption(f"更新時間：{now.strftime('%Y-%m-%d %H:%M:%S')}")

