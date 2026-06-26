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
# 🧠 AI 判讀（強制同水平線版本）
# =========================

st.subheader("🧠 AI 判讀")

signal = ai.get("signal", "HOLD")
score = ai.get("score", 50)
rebound = ai.get("rebound_prob", 50)

# =========================
# 🔥 CSS GRID（關鍵）
# =========================
st.markdown("""
<style>
.ai-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
    align-items: start;
}

.ai-box {
    padding: 12px;
    border-radius: 12px;
    background: #151a22;
    min-height: 110px;
}

.ai-title {
    font-size: 12px;
    color: #aaa;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 📦 左：訊號
# =========================
if signal == "BUY":
    signal_html = """
    <div class="ai-box" style="border-left:5px solid #ff1744;">
        <div class="ai-title">交易訊號</div>
        🔴 <b style="color:#ff5252;">做多訊號</b>
    </div>
    """
elif signal == "SELL":
    signal_html = """
    <div class="ai-box" style="border-left:5px solid #00e676;">
        <div class="ai-title">交易訊號</div>
        🟢 <b style="color:#00e676;">做空訊號</b>
    </div>
    """
else:
    signal_html = """
    <div class="ai-box">
        <div class="ai-title">交易訊號</div>
        ⚪ 盤整
    </div>
    """

# =========================
# 📦 中：AI信心
# =========================
ai_html = f"""
<div class="ai-box">
    <div class="ai-title">AI信心</div>
    <h2 style="margin:0;">{score}%</h2>
    <div style="background:#333;height:6px;border-radius:4px;">
        <div style="width:{score}%;background:#3b82f6;height:6px;border-radius:4px;"></div>
    </div>
</div>
"""

# =========================
# 📦 右：反彈機率
# =========================
if rebound >= 60:
    rebound_text = "🔴 強反彈"
elif rebound <= 40:
    rebound_text = "🟢 偏弱"
else:
    rebound_text = "⚪ 中性"

rebound_html = f"""
<div class="ai-box">
    <div class="ai-title">反彈機率</div>
    <h2 style="margin:0;">{rebound}%</h2>
    <div>{rebound_text}</div>
</div>
"""

# =========================
# 🚀 一次輸出（關鍵）
# =========================
st.markdown(f"""
<div class="ai-grid">
    {signal_html}
    {ai_html}
    {rebound_html}
</div>
""", unsafe_allow_html=True)

# =========================
# 📡 主力雷達（台股正確顏色版）
# =========================

st.subheader("📡 主力雷達")

bid_ratio = sum([b["size"] for b in bids]) / max(sum([a["size"] for a in asks]), 1)

# 🟢 偏多 = 紅色（台股漲）
if bid_ratio > 1.3:
    st.markdown("""
    <div style="color:#ff1744;font-weight:700;">
        🔴 主力吃貨（偏多）
    </div>
    """, unsafe_allow_html=True)

# 🔴 偏空 = 綠色（台股跌）
elif bid_ratio < 0.8:
    st.markdown("""
    <div style="color:#00e676;font-weight:700;">
        🟢 主力出貨（偏空）
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="color:#ffc107;font-weight:700;">
        🟡 籌碼平衡
    </div>
    """, unsafe_allow_html=True)

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
