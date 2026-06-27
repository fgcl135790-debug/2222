import streamlit as st

# =========================
# Page Config 必須盡量放最前面
# =========================

st.set_page_config(
    page_title="主力監控",
    layout="wide",
    page_icon="🏦",
)


# =========================
# Dashboard CSS
# =========================

st.markdown(
    """
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: #080c13;
}

header[data-testid="stHeader"] {
    background: #080c13;
    height: 40px;
}

.block-container {
    max-width: 1760px;
    padding: 2.25rem 0.55rem 0.6rem 0.55rem !important;
}

h1, h2, h3 {
    font-size: 14px !important;
    margin-top: 0 !important;
    margin-bottom: 0.18rem !important;
}

p, div, span {
    font-size: 12px;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.22rem;
}

div[data-testid="stHorizontalBlock"] {
    gap: 0.45rem;
}

hr {
    margin: 0.18rem 0 !important;
    border-color: rgba(255,255,255,0.07) !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 3px;
}

.stTabs [data-baseweb="tab"] {
    height: 28px;
    padding: 2px 7px;
    font-size: 11.5px;
}

.stDataFrame {
    font-size: 11.5px;
}

[data-testid="stSidebar"] {
    background: #0b111c;
}

button[kind="secondary"] {
    height: 28px;
    padding: 2px 8px;
}

.modebar {
    transform: scale(0.8);
    transform-origin: top right;
}

@media (max-width: 900px) {
    .block-container {
        padding: 2.2rem 0.45rem 0.6rem 0.45rem !important;
    }

    h1, h2, h3 {
        font-size: 13px !important;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# =========================
# Import 區：任何 import 錯誤都會顯示
# =========================

try:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from market_analyzer import MarketAnalyzer
    from ai_predictor import AIPredictor
    from decision_engine import DecisionEngine
    from big_order_engine import BigOrderEngine
    from trade_alert_engine import TradeAlertEngine
    from alert_engine import AlertEngine

    from ui.header import render_header
    from ui.chart_panel import render_chart
    from ui.depth_panel import render_depth_panel
    from ui.decision_card import render_decision_card
    from ui.rebound_panel import render_rebound_panel
    from ui.chip_panel import render_chip_panel
    from ui.alerts import render_alerts
    from ui.sidebar import render_sidebar

    from core.data_engine import get_market_data
    from streamlit_autorefresh import st_autorefresh

except Exception as e:
    st.error("程式在 import 階段就中斷，所以畫面才會空白。")
    st.exception(e)
    st.stop()


# =========================
# 小工具
# =========================

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def reset_state():
    st.session_state.price_history = []
    st.session_state.volume_history = []
    st.session_state.vwap_history = []
    st.session_state.big_order_log = []
    st.session_state.tick = 0
    st.session_state.last_serial = None
    st.session_state.big_order_last_serial = None
    st.session_state.last_good_quote = None
    st.session_state.api_error_message = None


def init_session_state():
    for k in ["price_history", "volume_history", "vwap_history"]:
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

    if "last_stock" not in st.session_state:
        st.session_state.last_stock = None

    if "last_good_quote" not in st.session_state:
        st.session_state.last_good_quote = None

    if "api_error_message" not in st.session_state:
        st.session_state.api_error_message = None


# =========================
# 主程式
# =========================

def main():

    init_session_state()

    now = datetime.now(ZoneInfo("Asia/Taipei"))

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
        key="v75_dashboard_refresh",
    )

    # =========================
    # 取得資料
    # =========================

    if data_source == "真實盤" and not api_key:
        st.warning("請輸入 API KEY，或先切換到模擬盤測試 UI。")
        st.stop()

    try:
        with st.spinner("取得行情資料中..."):
            quote = get_market_data(
                data_source=data_source,
                api_key=api_key,
                stock_code=stock_code,
                tick=st.session_state.tick,
            )

        if not quote:
            raise ValueError("empty quote")

        st.session_state.last_good_quote = quote
        st.session_state.api_error_message = None

    except Exception as e:
        st.session_state.api_error_message = type(e).__name__

        if st.session_state.last_good_quote is not None:
            quote = st.session_state.last_good_quote

            st.warning(
                f"資料來源暫時異常，已使用上一筆有效資料。錯誤：{type(e).__name__}"
            )

        else:
            st.error("Fugle API 暫時異常，且目前沒有上一筆有效資料可使用。")
            st.exception(e)
            st.stop()

    if data_source == "模擬盤":
        st.session_state.tick += 1

    # =========================
    # Quote 解析
    # =========================

    name = quote.get("name", "Unknown")
    price = _safe_float(quote.get("price", 0))
    vwap = _safe_float(quote.get("vwap", price), price)
    volume = _safe_float(quote.get("last_size", 0))

    bids = quote.get("bids", []) or []
    asks = quote.get("asks", []) or []

    trade = quote.get("trade", {}) or {}
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
        st.session_state.last_good_quote = quote

    # =========================
    # 歷史資料
    # =========================

    if st.session_state.last_serial != serial:
        st.session_state.last_serial = serial

        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)
        st.session_state.vwap_history.append(vwap)

        if len(st.session_state.price_history) > 500:
            st.session_state.price_history = st.session_state.price_history[-500:]
            st.session_state.volume_history = st.session_state.volume_history[-500:]
            st.session_state.vwap_history = st.session_state.vwap_history[-500:]

    prices = st.session_state.price_history
    volumes = st.session_state.volume_history
    vwaps = st.session_state.vwap_history

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

    bid_total = sum([_safe_float(b.get("size", 0)) for b in bids])
    ask_total = sum([_safe_float(a.get("size", 0)) for a in asks])

    bid_ratio = bid_total / max(ask_total, 1)

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

    signal = ai.get("signal", "WAIT")
    score = ai.get("score", 0)
    risk = ai.get("risk", "監控中")
    state = ai.get("market_state", "資料累積中")
    rebound = ai.get("rebound_prob", 0)

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

    # =========================
    # Trade Alert
    # =========================

    trade_alert = TradeAlertEngine.track(
        decision=decision,
        price=price,
    )

    # =========================
    # Alert Engine
    # =========================

    alerts = AlertEngine.build(
        decision=decision,
        trade_alert=trade_alert,
        big_order_log=st.session_state.big_order_log,
    )

    # =========================
    # Header
    # =========================

    connection_status = (
        "資料延遲"
        if st.session_state.get("api_error_message")
        else "連線正常"
    )

    render_header(
        name=name,
        stock_code=stock_code,
        price=price,
        score=score,
        rebound=rebound,
        risk=risk,
        state=state,
        signal=signal,
        bid_ratio=bid_ratio,
        now=now,
        connection_status=connection_status,
        data_source=data_source,
    )

    # =========================
    # V7.5 Dashboard Layout
    # =========================

    main_left, main_right = st.columns([1.72, 1])

    # =========================
    # 左側：主圖 + 唯一五檔 / 多空區
    # =========================

    with main_left:
        render_chart(
            prices=prices,
            volumes=volumes,
            vwap_values=vwaps,
        )

        render_depth_panel(
            bids=bids,
            asks=asks,
            decision=decision,
        )

    # =========================
    # 右側：警示 + 決策 + 反彈 + 籌碼結論
    # =========================

    with main_right:
        # 1. 核心交易決策
        render_decision_card(decision)

        # 2. 即時警示
        render_alerts(alerts)

        # 3. 反彈 / 假突破分析
        render_rebound_panel(
            decision=decision,
            trade_alert=trade_alert,
        )

        # 4. 主力籌碼結論
        render_chip_panel(
            bids=bids,
            asks=asks,
            big_order_log=st.session_state.big_order_log,
            decision=decision,
        )


# =========================
# Run
# =========================

try:
    main()

except Exception as e:
    st.error("程式執行途中發生錯誤，所以剛剛才會整頁空白。")
    st.exception(e)
