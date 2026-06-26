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
# 🧠 V5.5 券商級設定
# =========================

st.set_page_config(
    page_title="V5.5 券商主力雷達",
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
# 🧠 Sidebar（券商級控制中心）
# =========================
with st.sidebar:

    st.title("⚙️ V5.5 控制中心")

    stock_code = st.text_input("股票代號", "2330")

    data_source = st.radio("資料來源", ["真實盤", "模擬盤"])

    api_key = st.text_input("Fugle API Key", type="password")

    mode = st.selectbox("AI模式", ["一般", "激進", "保守"])

    refresh_sec = st.slider("更新秒數", 1, 5, 2)

    if st.button("重置股票"):
        reset_state()
        st.rerun()


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
st.title(f"🏦 V5.5 {name} ({stock_code})")

colA, colB, colC, colD = st.columns(4)

colA.metric("現價", price)
colB.metric("AI信心", f"{score}%")
colC.metric("風險", f"{risk}%")
colD.metric("狀態", state)


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
# AI 判讀（V5.5 券商排版修正版）
# =========================

st.subheader("🧠 AI 判讀")

col1, col2, col3 = st.columns(3)

# =========================
# 左：做空/做多訊號
# =========================
with col1:
    if signal == "BUY":
        st.markdown(
            """
            <div style="background:#3b0d0d;padding:12px;border-radius:10px;">
                <span style="color:#ff5252;font-weight:700;">🔴 做多訊號</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    elif signal == "SELL":
        st.markdown(
            """
            <div style="background:#0d3b1f;padding:12px;border-radius:10px;">
                <span style="color:#00e676;font-weight:700;">🟢 做空訊號</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    else:
        st.markdown("⚪ 盤整")

# =========================
# 中：AI 信心
# =========================
with col2:
    st.metric("AI信心", f"{ai_confidence}%")

    st.progress(ai_confidence / 100)

# =========================
# 右：反彈機率
# =========================
with col3:
    st.metric("反彈機率", f"{rebound_rate}%")

    if rebound_rate > 60:
        st.success("可能反彈")
    elif rebound_rate < 40:
        st.error("偏弱")
    else:
        st.info("中性")

# =========================
# 📊 主力雷達（簡化券商版）
# =========================
st.subheader("📡 主力雷達")

bid_ratio = sum([b["size"] for b in bids]) / max(sum([a["size"] for a in asks]), 1)

if bid_ratio > 1.3:
    st.success("🟢 主力偏多（吃貨）")
elif bid_ratio < 0.8:
    st.error("🔴 主力偏空（出貨）")
else:
    st.info("🟡 籌碼平衡")


# =========================
# 📈 走勢圖（修復清空問題）
# =========================
st.subheader("📈 分時趨勢")

fig = ChartBuilder.build_price_chart(prices, volumes)
st.plotly_chart(fig, use_container_width=True)


# =========================
# 📋 五檔（券商級）
# =========================
st.subheader("📋 五檔報價")

while len(bids) < 5:
    bids.append({"price": 0, "size": 0})

while len(asks) < 5:
    asks.append({"price": 0, "size": 0})

df = pd.DataFrame({
    "買價": [b["price"] for b in bids[:5]],
    "買量": [b["size"] for b in bids[:5]],
    "賣價": [a["price"] for a in asks[:5]],
    "賣量": [a["size"] for a in asks[:5]],
})

st.dataframe(df, use_container_width=True)
