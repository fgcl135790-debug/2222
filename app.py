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

/* Streamlit 上方列 */
header[data-testid="stHeader"] {
    background: #080c13;
    height: 38px;
}

/* 主內容寬度 */
.block-container {
    max-width: 1840px;
    padding: 2.05rem 0.55rem 0.6rem 0.55rem !important;
}

/* 壓縮標題 */
h1, h2, h3 {
    font-size: 14px !important;
    margin-top: 0 !important;
    margin-bottom: 0.16rem !important;
}

/* 全域字體 */
p, div, span {
    font-size: 12px;
}

/* 壓縮垂直間距 */
div[data-testid="stVerticalBlock"] {
    gap: 0.20rem;
}

/* 壓縮左右欄位間距 */
div[data-testid="stHorizontalBlock"] {
    gap: 0.40rem;
}

/* 分隔線 */
hr {
    margin: 0.16rem 0 !important;
    border-color: rgba(255,255,255,0.07) !important;
}

/* 側邊欄 */
[data-testid="stSidebar"] {
    background: #0b111c;
}

/* 按鈕 */
button[kind="secondary"] {
    height: 28px;
    padding: 2px 8px;
}

/* Plotly 工具列縮小 */
.modebar {
    transform: scale(0.78);
    transform-origin: top right;
}

/* 表格 */
.stDataFrame {
    font-size: 11.5px;
}

/* Expander 壓縮 */
[data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    background: rgba(255,255,255,0.025);
}

[data-testid="stExpander"] details {
    padding: 0;
}

/* 隱藏 footer */
footer {
    visibility: hidden;
}

/* 手機版 */
@media (max-width: 900px) {
    .block-container {
        padding: 2.0rem 0.45rem 0.6rem 0.45rem !important;
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
    import random
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from market_analyzer import MarketAnalyzer
    from ai_predictor import AIPredictor
    from decision_engine import DecisionEngine
    from multi_period_engine import MultiPeriodEngine
    from big_order_engine import BigOrderEngine
    from trade_alert_engine import TradeAlertEngine
    from alert_engine import AlertEngine
    from market_flow_engine import MarketFlowEngine

    from ui.header import render_header
    from ui.chart_panel import render_chart
    from ui.lower_market_grid import render_lower_market_grid
    from ui.decision_card import render_decision_card
    from ui.rebound_panel import render_rebound_panel
    from ui.main_force_panel import render_main_force_panel
    from ui.alerts import render_alerts
    from ui.sidebar import render_sidebar
    from ui.event_stream_panel import render_event_stream_panel

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
    MarketFlowEngine.reset_market_state(st)

    # 手動重置時，下一次會重新建立模擬路徑
    st.session_state.market_context_key = None
    st.session_state.sim_run_id = random.randint(100000, 999999)


def init_session_state():
    MarketFlowEngine.init_session_state(st)


# =========================
# 主程式
# =========================

def main():

    init_session_state()

    if "market_context_key" not in st.session_state:
        st.session_state.market_context_key = None

    if "sim_run_id" not in st.session_state:
        st.session_state.sim_run_id = random.randint(100000, 999999)

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
    # 切換股票 / 資料來源 / 模擬模式時清空
    # =========================

    context_key = f"{stock_code}|{data_source}|{mode}"
    old_context_key = st.session_state.get("market_context_key")

    if old_context_key != context_key:
        MarketFlowEngine.reset_market_state(
            st=st,
            keep_stock=stock_code,
        )

        st.session_state.market_context_key = context_key

        # 只有切換情境 / 股票 / 資料來源時，才重新產生模擬走勢
        # 不能每次 refresh 都 random
        if data_source == "模擬盤":
            st.session_state.sim_run_id = random.randint(100000, 999999)
            
    # =========================
    # Auto Refresh
    # =========================

    chart_fullscreen = st.session_state.get("chart_fullscreen", False)

    if not chart_fullscreen:
        st_autorefresh(
            interval=refresh_sec * 1000,
            key="v75_dashboard_refresh",
        )
    else:
        st.info("圖表全屏檢視中，自動刷新已暫停。按圖表工具列的「返回」恢復。")

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
                mode=mode,
                sim_run_id=st.session_state.get("sim_run_id", 0),
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

    # 模擬盤才每次刷新推進 tick
    if data_source == "模擬盤":
        st.session_state.tick += 1

    # =========================
    # 統一資料流 Snapshot
    # 真實盤休市後，serial 不會再用現在時間，所以不會一直新增假資料
    # =========================

    snapshot = MarketFlowEngine.build_snapshot(
        st=st,
        quote=quote,
        stock_code=stock_code,
        now=now,
        data_source=data_source,
    )

    name = snapshot["name"]
    price = snapshot["price"]
    vwap = snapshot["vwap"]
    volume = snapshot["volume"]
    high = snapshot["high"]
    low = snapshot["low"]
    bids = snapshot["bids"]
    asks = snapshot["asks"]
    serial = snapshot["serial"]
    market_status = snapshot.get("market_status", "未知")

    prices = snapshot["prices"]
    volumes = snapshot["volumes"]
    vwaps = snapshot["vwaps"]
    times = snapshot["times"]

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

    bid_total = sum(
        [
            _safe_float(b.get("size", 0))
            for b in bids
        ]
    )

    ask_total = sum(
        [
            _safe_float(a.get("size", 0))
            for a in asks
        ]
    )

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
    # Multi Period Engine
    # =========================

    multi_period = MultiPeriodEngine.analyze(
        prices=prices,
        volumes=volumes,
        vwap_values=vwaps,
        time_values=times,
    )

    decision = MultiPeriodEngine.apply_to_decision(
        decision=decision,
        multi_period=multi_period,
    )

    # =========================
    # Header 同步最終決策結果
    # =========================

    final_action = decision.get("action", "WAIT")
    final_score = decision.get("score", score)
    final_rebound = decision.get("rebound", rebound)
    final_state = decision.get("multi_period_status", state)

    score = final_score
    signal = final_action
    rebound = final_rebound

    if final_action == "BUY":
        state = f"多方監控｜{final_state}"

    elif final_action == "SELL":
        state = f"空方監控｜{final_state}"

    else:
        state = f"等待確認｜{final_state}"

    # 休市時，Header 狀態補上休市提醒，但不影響決策卡內容
    if data_source == "真實盤" and market_status == "休市":
        state = f"休市｜{state}"

    if score >= 80:
        risk = "方向明確"

    elif score >= 65:
        risk = "可觀察"

    elif score <= 40:
        risk = "高風險"

    else:
        risk = "等待確認"

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

    if st.session_state.get("api_error_message"):
        connection_status = "資料延遲"
    elif data_source == "真實盤" and market_status == "休市":
        connection_status = "休市快照"
    else:
        connection_status = "連線正常"

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
    # 全屏圖表模式
    # =========================

    if st.session_state.get("chart_fullscreen", False):
        render_chart(
            prices=prices,
            volumes=volumes,
            vwap_values=vwaps,
            time_values=times,
            decision=decision,
            trade_alert=trade_alert,
        )
        return

    # =========================
    # V7.6 Dashboard Layout
    # =========================

    main_left, main_right = st.columns(
        [1.92, 0.92],
        gap="small",
    )

    # =========================
    # 左側：主圖 + 市場資訊 + 大單事件流
    # =========================

    with main_left:
        render_chart(
            prices=prices,
            volumes=volumes,
            vwap_values=vwaps,
            time_values=times,
            decision=decision,
            trade_alert=trade_alert,
        )

        render_lower_market_grid(
            bids=bids,
            asks=asks,
            decision=decision,
            price=price,
            vwap=vwap,
            ema5=ema5,
            ema20=ema20,
            rsi=rsi,
            macd=macd,
            macd_signal=macd_signal,
            volume=volume,
            volumes=volumes,
        )

        render_event_stream_panel(
            big_order_log=st.session_state.big_order_log,
            decision=decision,
        )

    # =========================
    # 右側：決策 + 反彈 + 主力 + 警示
    # =========================

    with main_right:
        render_decision_card(decision)

        render_rebound_panel(
            decision=decision,
            trade_alert=trade_alert,
        )

        render_main_force_panel(
            bids=bids,
            asks=asks,
            big_order_log=st.session_state.big_order_log,
            decision=decision,
        )

        render_alerts(alerts)


# =========================
# Run
# =========================

try:
    main()

except Exception as e:
    st.error("程式執行途中發生錯誤，所以剛剛才會整頁空白。")
    st.exception(e)
