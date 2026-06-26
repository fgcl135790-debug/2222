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

for k in ["price_history", "volume_history", "big_order_log", "last_serial", "tick"]:
    if k not in st.session_state:
        st.session_state[k] = [] if "history" in k or "log" in k else 0


# =========================
# Sidebar（V4控制）
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
# Quote 解包（穩定版）
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
# History（🔥修復：不更新問題核心）
# =========================

if market_open and not is_close:

    if (
        len(st.session_state.price_history) == 0
        or trade_serial != st.session_state.last_serial
    ):

        st.session_state.last_serial = trade_serial

        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)


# =========================
# 限制長度（避免爆炸）
# =========================

st.session_state.price_history = st.session_state.price_history[-300:]
st.session_state.volume_history = st.session_state.volume_history[-300:]


prices = st.session_state.price_history
volumes = st.session_state.volume_history


# =========================
# 五檔安全修復（避免消失）
# =========================

if len(bids) < 5:
    bids += [{"price": 0, "size": 0}] * (5 - len(bids))

if len(asks) < 5:
    asks += [{"price": 0, "size": 0}] * (5 - len(asks))


# =========================
# 技術指標（法人穩定版）
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
# 買賣盤（法人級）
# =========================

total_bid = sum(x["size"] for x in bids)
total_ask = sum(x["size"] for x in asks)

bid_ratio = total_bid / max(total_ask, 1)


# =========================
# 🧠 V4 法人AI（穩定核心）
# =========================

ai_score = 50
reasons = []


# ===== 趨勢濾波（防亂跳核心）=====
trend_strength = ema20 - ema60

if abs(trend_strength) < price * 0.001:
    ai_score += 0
    reasons.append("盤整區（法人觀望）")

elif trend_strength > 0:
    ai_score += 10
    reasons.append("多頭趨勢成立")

else:
    ai_score -= 10
    reasons.append("空頭趨勢成立")


# ===== VWAP（法人基準）=====
if price > vwap:
    ai_score += 10
    reasons.append("站上VWAP（多方）")
else:
    ai_score -= 10
    reasons.append("跌破VWAP（空方）")


# ===== 均線結構（核心）=====
if ema5 > ema20 > ema60:
    ai_score += 20
    reasons.append("多頭排列（法人進場）")

elif ema5 < ema20 < ema60:
    ai_score -= 20
    reasons.append("空頭排列（法人出貨）")


# ===== RSI（降敏感）=====
if 40 <= rsi <= 60:
    ai_score += 5
    reasons.append("RSI中性")

elif rsi > 75:
    ai_score -= 10
    reasons.append("RSI過熱")

elif rsi < 30:
    ai_score += 10
    reasons.append("RSI超賣")


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
    reasons.append("量能放大")
elif volume_trend == "DOWN":
    ai_score -= 10
    reasons.append("量能縮減")


# ===== 委買委賣（主力）=====
if bid_ratio > 2:
    ai_score += 15
    reasons.append("強力吃單")

elif bid_ratio > 1.3:
    ai_score += 8
    reasons.append("買盤偏強")

elif bid_ratio < 0.7:
    ai_score -= 15
    reasons.append("賣壓沉重")


# ===== 波動過濾（防假訊號）=====
if volatility > 3:
    ai_score -= 5

elif volatility < 0.5:
    ai_score -= 3


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
    action = "⚪ 盤整觀望"

elif ai_score >= 35:
    action = "📉 偏空（法人減碼）"

else:
    action = "💥 強力出貨"


confidence = ai_score


# =========================
# Header
# =========================

st.title(f"🏦 準法人交易系統 V4 - {name} ({stock_code})")

st.caption(f"更新時間：{now.strftime('%Y-%m-%d %H:%M:%S')}")


# =========================
# Chart
# =========================

st.subheader("📊 即時走勢")

fig = ChartBuilder.build_price_chart(prices, volumes)

st.plotly_chart(fig, use_container_width=True)


# =========================
# 指標列
# =========================

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("現價", round(price, 2))
c2.metric("VWAP", round(vwap, 2))
c3.metric("EMA5", round(float(ema5), 2))
c4.metric("EMA20", round(float(ema20), 2))
c5.metric("RSI", rsi)
c6.metric("MACD", round(macd, 3))


st.markdown("---")


# =========================
# AI區塊
# =========================

col1, col2, col3, col4 = st.columns(4)


# =========================
# AI交易判斷（顏色修正）
# =========================

with col1:

    st.subheader("🤖 AI判斷")

    if "做多" in action:
        st.success(f"🟢 {action} {confidence}%")

    elif "偏多" in action:
        st.info(f"📈 {action} {confidence}%")

    elif "偏空" in action:
        st.warning(f"📉 {action} {confidence}%")

    else:
        st.error(f"🔴 {action} {confidence}%")

    st.progress(confidence / 100)

    st.markdown("#### AI理由")

    for r in reasons:
        st.write("•", r)


# =========================
# AI反轉
# =========================

with col2:

    st.subheader("🔄 反轉訊號")

    reversal = AIPredictor.predict_reversal(
        price,
        prices,
        vwap,
        ema5,
        ema20,
        ema60,
        rsi,
        macd,
        macd_signal,
        total_bid,
        total_ask,
        momentum,
    )

    st.write(reversal[1])
    st.metric("信心", f"{reversal[2]}%")
    st.progress(reversal[2] / 100)
    st.write(reversal[3])


# =========================
# 技術分析
# =========================

with col3:

    st.subheader("📊 技術面")

    st.metric("Momentum", round(momentum, 2))

    st.metric("波動率", f"{volatility}%")

    st.metric("成交量趨勢", volume_trend)

    st.metric("RSI", rsi)

    st.metric("MACD Hist", round(macd_hist, 3))


# =========================
# 五檔（法人版）
# =========================

with col4:

    st.subheader("🏦 五檔")

    bid_list = bids[:5]
    ask_list = asks[:5]

    st.dataframe(
        pd.DataFrame({
            "買價": [x["price"] for x in bid_list],
            "買量": [x["size"] for x in bid_list],
            "賣價": [x["price"] for x in ask_list],
            "賣量": [x["size"] for x in ask_list],
        }),
        use_container_width=True,
        hide_index=True,
        height=220,
    )


st.markdown("---")


# =========================
# 漲停機率（穩定版）
# =========================

limit_score = 10

if price > vwap:
    limit_score += 15

if ema5 > ema20:
    limit_score += 15

if ema20 > ema60:
    limit_score += 10

if bid_ratio > 1.5:
    limit_score += 15

if momentum > 2:
    limit_score += 10

if rsi < 70:
    limit_score += 5

if macd > macd_signal:
    limit_score += 10

if volume_trend == "UP":
    limit_score += 10

limit_score = max(0, min(int(limit_score), 100))

st.metric("🚀 漲停機率", f"{limit_score}%")
st.progress(limit_score / 100)


st.markdown("---")


# =========================
# 主力狀態
# =========================

if bid_ratio > 2:
    st.success("🔴 主力積極吃單")

elif bid_ratio > 1.3:
    st.info("📈 主力偏多")

elif bid_ratio < 0.7:
    st.error("🟢 主力出貨")

else:
    st.warning("⚪ 中性")
# =========================
# 五檔 + 明細區（V4補完）
# =========================

st.markdown("---")

tab1, tab2, tab3 = st.tabs([
    "📜 成交紀錄",
    "📋 五檔",
    "📥 匯出"
])

# =========================
# 成交紀錄
# =========================

with tab1:

    st.subheader("📜 大戶成交紀錄")

    if len(st.session_state.big_order_log) > 0:

        log_df = pd.DataFrame(st.session_state.big_order_log)

        st.dataframe(
            log_df,
            use_container_width=True,
            hide_index=True,
            height=300
        )

    else:

        st.info("尚未偵測到大戶成交")


# =========================
# 五檔
# =========================

with tab2:

    st.subheader("📋 五檔報價")

    bid_list = bids.copy()
    ask_list = asks.copy()

    while len(bid_list) < 5:
        bid_list.append({"price": 0, "size": 0})

    while len(ask_list) < 5:
        ask_list.append({"price": 0, "size": 0})

    best5_df = pd.DataFrame({
        "買價": [x["price"] for x in bid_list[:5]],
        "買量": [x["size"] for x in bid_list[:5]],
        "賣價": [x["price"] for x in ask_list[:5]],
        "賣量": [x["size"] for x in ask_list[:5]],
    })

    st.dataframe(
        best5_df,
        use_container_width=True,
        hide_index=True,
        height=220
    )


# =========================
# 匯出
# =========================

with tab3:

    st.subheader("📥 匯出資料")

    csv_data = Exporter.export_big_order_log(
        st.session_state.big_order_log
    )

    st.download_button(
        "📥 下載大戶成交紀錄",
        csv_data,
        file_name="big_order_log.csv",
        mime="text/csv"
    )

    st.info(f"目前共有 {len(st.session_state.big_order_log)} 筆紀錄")

# =========================
# Footer
# =========================

st.markdown("---")

st.caption("V4 準法人交易系統 | AI Institutional Flow Engine")
