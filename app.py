import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

from market_analyzer import MarketAnalyzer
from ai_predictor import AIPredictor
from decision_engine import DecisionEngine
from big_order_engine import BigOrderEngine
from trade_alert_engine import TradeAlertEngine
from alert_engine import AlertEngine

from ui.header import render_header
from ui.ai_panel import render_ai_panel
from ui.orderbook import render_orderbook
from ui.radar import render_radar
from ui.chart_panel import render_chart
from ui.decision_card import render_decision_card
from ui.trade_alert_panel import render_trade_alert_panel
from ui.power_panel import render_power_panel
from ui.sidebar import render_sidebar
from ui.big_order_panel import render_big_order_panel
from ui.alerts import render_alerts

from core.data_engine import get_market_data
from streamlit_autorefresh import st_autorefresh


# =========================
# 系統設定
# =========================

st.set_page_config(
    page_title="主力監控",
    layout="wide",
    page_icon="🏦"
)

st.markdown("""
<style>
.block-container {
    padding: 0.35rem 0.75rem;
    font-size: 13px;
}

h1, h2, h3 {
    font-size: 16px !important;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.35rem;
}

div[data-testid="stHorizontalBlock"] {
    gap: 0.6rem;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    height: 32px;
    padding: 4px 8px;
    font-size: 12px;
}

.stDataFrame {
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 台灣時間
# =========================

now = datetime.now(ZoneInfo("Asia/Taipei"))


# =========================
# Session Reset
# =========================

def reset_state():
    st.session_state.price_history = []
    st.session_state.volume_history = []
    st.session_state.big_order_log = []
    st.session_state.tick = 0
    st.session_state.last_serial = None
    st.session_state.big_order_last_serial = None


for k in ["price_history", "volume_history"]:
    if k not in st.session_state:
        st.session_state[k] = []

if "big_order_log" not in st.session_state:
    st.session_state.big_order_log = []

if "tick" not in st.session_state:
    st.session_state.tick = 0

if "last_serial" not in st.session_state:
    st.session_state.last_serial = None

if "big_order_last_serial" not in st.session_state:
    st.session_state.big_order_last_serial = None


# =========================
# Sidebar
# =========================

(
    stock_code,
    data_source,
    api_key,
    mode,
    refresh_sec,
) = render_sidebar(reset_state)


# =========================
# Auto Refresh
# =========================

st_autorefresh(
    interval=refresh_sec * 1000,
    key="v75_refresh"
)


# =========================
# 取得資料
# =========================

if data_source == "真實盤" and not api_key:
    st.warning("請輸入 API KEY")
    st.stop()

quote = get_market_data(
    data_source=data_source,
    api_key=api_key,
    stock_code=stock_code,
    tick=st.session_state.tick,
)

if data_source == "模擬盤":
    st.session_state.tick += 1


# =========================
# Quote 解析
# =========================

name = quote.get("name", "Unknown")
price = quote.get("price", 0)
vwap = quote.get("vwap", 0)
volume = quote.get("last_size", 0)

bids = quote.get("bids", [])
asks = quote.get("asks", [])

trade = quote.get("trade", {})
raw_serial = trade.get("serial", None)

if raw_serial:
    serial = raw_serial
else:
    serial = f"{stock_code}_{st.session_state.tick}_{price}_{volume}"


# =========================
# 換股清空
# =========================

if st.session_state.get("last_stock") != stock_code:
    reset_state()
    st.session_state.last_stock = stock_code


# =========================
# 歷史資料
# =========================

if st.session_state.last_serial != serial:
    st.session_state.last_serial = serial
    st.session_state.price_history.append(price)
    st.session_state.volume_history.append(volume)

prices = st.session_state.price_history
volumes = st.session_state.volume_history

# =========================
# 主力大單偵測
# =========================

if st.session_state.big_order_last_serial != serial:

    st.session_state.big_order_last_serial = serial

    big_order = BigOrderEngine.detect(
        stock_code=stock_code,
        name=name,
        price=price,
        volume=volume,
        bids=bids,
        asks=asks,
        prices=prices,
        volumes=volumes,
    )

    if big_order is not None:

        st.session_state.big_order_log.append(big_order)

        if len(st.session_state.big_order_log) > 100:
            st.session_state.big_order_log = st.session_state.big_order_log[-100:]

# =========================
# 技術指標
# =========================

ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)
ema60 = MarketAnalyzer.calculate_ema(prices, 60)

rsi = MarketAnalyzer.calculate_rsi(prices)

macd, macd_signal, _ = MarketAnalyzer.calculate_macd(prices)

momentum = MarketAnalyzer.momentum(prices)

# =========================
# 五檔買賣力道
# =========================

bid_ratio = (
    sum([b.get("size", 0) for b in bids])
    /
    max(sum([a.get("size", 0) for a in asks]), 1)
)

# =========================
# AI Predict
# =========================

ai = AIPredictor.predict_trade(
    prices,
    volumes,
    ema5,
    ema20,
    ema60,
    rsi,
    macd,
    macd_signal,
    momentum,
    bid_ratio=bid_ratio,
    vwap=vwap,
)

signal = ai["signal"]
score = ai["score"]
risk = ai["risk"]
state = ai["market_state"]
rebound = ai["rebound_prob"]


# =========================
# Decision Engine
# =========================

decision = DecisionEngine.generate(
    ai=ai,
    price=price,
    vwap=vwap,
    ema5=ema5,
    ema20=ema20,
    ema60=ema60,
    rsi=rsi,
    macd=macd,
    macd_signal=macd_signal,
    bid_ratio=bid_ratio,
    prices=prices,
    volumes=volumes,
)

trade_alert = TradeAlertEngine.track(
    decision=decision,
    price=price,
)

alerts = AlertEngine.build(
    decision=decision,
    trade_alert=trade_alert,
    big_order_log=st.session_state.big_order_log,
)

# =========================
# Header
# =========================

render_header(
    name=name,
    stock_code=stock_code,
    price=price,
    score=score,
    risk=risk,
    state=state,
)


# =========================
# V7.5 主畫面
# =========================

left, right = st.columns([2.2, 1])


# =========================
# 左側
# =========================

with left:

    render_ai_panel(
        signal=signal,
        score=score,
        rebound=rebound,
    )

    render_chart(
        prices=prices,
        volumes=volumes,
    )


# =========================
# 右側
# =========================

with right:

    render_alerts(alerts)

    st.divider()

    render_decision_card(decision)

    st.divider()

    render_trade_alert_panel(trade_alert)

    st.divider()

    tab_power, tab_big_order, tab_radar, tab_orderbook = st.tabs(
        [
            "⚔️ 多空",
            "🐋 大單",
            "📡 雷達",
            "📋 五檔",
        ]
    )

    with tab_power:

        render_power_panel(decision)

    with tab_big_order:

        render_big_order_panel(
            st.session_state.big_order_log
        )

    with tab_radar:

        render_radar(
            bids=bids,
            asks=asks,
        )

    with tab_orderbook:

        render_orderbook(
            bids=bids,
            asks=asks,
        )
