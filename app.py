import streamlit as st
import pandas as pd

from datetime import datetime
from zoneinfo import ZoneInfo

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from charts import ChartBuilder
from exporters import Exporter

from streamlit_autorefresh import st_autorefresh

# =========================
# Page Config
# =========================

st.set_page_config(
    page_title="REST PRO v3",
    page_icon="⚡",
    layout="wide",
)

# =========================
# UI Style
# =========================

st.markdown("""
<style>

.block-container{
    padding-top:0.4rem;
    padding-bottom:0.4rem;
    padding-left:0.8rem;
    padding-right:0.8rem;
}

div[data-testid="stMetric"]{
    padding:8px;
}

div[data-testid="stMetricValue"]{
    font-size:24px;
}

div[data-testid="stMetricLabel"]{
    font-size:14px;
}

h1{
    font-size:32px !important;
}

h2{
    font-size:24px !important;
}

h3{
    font-size:18px !important;
}

.stDataFrame{
    font-size:13px;
}

</style>
""", unsafe_allow_html=True)

# =========================
# Auto Refresh
# =========================

refresh_count = st_autorefresh(
    interval=2000,
    key="refresh",
)

# =========================
# 台灣時間
# =========================

taipei_time = datetime.now(
    ZoneInfo("Asia/Taipei")
)
# =========================
# Session State
# =========================

avg_volume = 1
suggest_threshold = 100

# -------------------------
# 歷史資料
# -------------------------

if "price_history" not in st.session_state:
    st.session_state.price_history = []

if "volume_history" not in st.session_state:
    st.session_state.volume_history = []

if "big_order_log" not in st.session_state:
    st.session_state.big_order_log = []

# -------------------------
# 去重複用
# -------------------------

if "last_history_serial" not in st.session_state:
    st.session_state.last_history_serial = None

if "last_big_order_serial" not in st.session_state:
    st.session_state.last_big_order_serial = None

# -------------------------
# 股票切換
# -------------------------

if "current_stock" not in st.session_state:
    st.session_state.current_stock = None

# -------------------------
# 模擬Tick
# -------------------------

if "tick" not in st.session_state:
    st.session_state.tick = 0

# =========================
# Sidebar
# =========================

with st.sidebar:

    st.header("⚙️ 系統設定")

    data_source = st.radio(
        "資料來源",
        [
            "真實盤",
            "情境模擬",
        ],
    )

    stock_code = st.text_input(
        "股票代號",
        "2330",
    )

    # 股票切換自動清空所有資料
    if st.session_state.current_stock != stock_code:

        st.session_state.current_stock = stock_code

        st.session_state.price_history.clear()
        st.session_state.volume_history.clear()
        st.session_state.big_order_log.clear()

        st.session_state.last_history_serial = None
        st.session_state.last_big_order_serial = None

        st.session_state.tick = 0

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

    st.divider()

    auto_threshold = st.checkbox(
        "自動大戶門檻",
        value=True,
    )

    if len(st.session_state.volume_history) > 0:

        avg_volume = (
            sum(st.session_state.volume_history[-100:])
            /
            min(
                len(st.session_state.volume_history),
                100,
            )
        )

        suggest_threshold = max(
            100,
            int(avg_volume * 3),
        )

        st.info(
            f"最近100筆平均量：{avg_volume:.0f} 張\n\n"
            f"建議門檻：{suggest_threshold} 張"
        )

    else:

        suggest_threshold = 100

    if auto_threshold:

        big_order_threshold = suggest_threshold

        st.success(
            f"目前門檻：{big_order_threshold} 張"
        )

    else:

        big_order_threshold = st.number_input(
            "大戶門檻",
            min_value=10,
            max_value=10000,
            value=100,
            step=10,
        )

    sim_minutes = st.slider(
        "模擬時間(分鐘)",
        2,
        60,
        10,
    )

    if st.button("🔄 重置全部"):

        st.session_state.price_history.clear()
        st.session_state.volume_history.clear()
        st.session_state.big_order_log.clear()

        st.session_state.last_history_serial = None
        st.session_state.last_big_order_serial = None

        st.session_state.tick = 0

        st.rerun()

# =========================
# Data Provider
# =========================

try:

    if data_source == "真實盤":

        if not api_key:

            st.warning("請輸入 Fugle API Key")
            st.stop()

        provider = FugleProvider(api_key)

        quote = provider.get_quote(
            stock_code
        )

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
# Quote
# =========================

name = quote.get(
    "name",
    stock_code,
)

price = quote.get(
    "price",
    0,
)

vwap = quote.get(
    "vwap",
    price,
)

volume = quote.get(
    "last_size",
    0,
)

bids = quote.get(
    "bids",
    [],
)

asks = quote.get(
    "asks",
    [],
)

trade = quote.get(
    "trade",
    {},
)

trade_serial = trade.get(
    "serial",
    0,
)

is_close = quote.get(
    "is_close",
    False,
)

# =========================
# 市場時間
# =========================

now = datetime.now(
    ZoneInfo("Asia/Taipei")
)

market_open = (

    (
        now.hour > 9
        or
        (
            now.hour == 9
            and
            now.minute >= 0
        )
    )

    and

    (

        now.hour < 13

        or

        (
            now.hour == 13
            and
            now.minute <= 30
        )

    )

)

# =========================
# Auto Refresh Status
# =========================

if market_open and not is_close:

    st.sidebar.success(
        "🟢 盤中即時更新"
    )

else:

    st.sidebar.warning(
        "🔴 非交易時間"
    )

# =========================
# History
# =========================

if (

    market_open

    and

    not is_close

    and

    trade_serial != st.session_state.last_history_serial

):

    st.session_state.last_history_serial = trade_serial

    st.session_state.price_history.append(
        price
    )

    st.session_state.volume_history.append(
        volume
    )

st.session_state.price_history = (
    st.session_state.price_history[-500:]
)

st.session_state.volume_history = (
    st.session_state.volume_history[-500:]
)

prices = st.session_state.price_history

volumes = st.session_state.volume_history

# =========================
# Indicators
# =========================

ema5 = MarketAnalyzer.calculate_ema(
    prices,
    5,
)

ema20 = MarketAnalyzer.calculate_ema(
    prices,
    20,
)

ema60 = MarketAnalyzer.calculate_ema(
    prices,
    60,
)

trend = MarketAnalyzer.trend(
    price,
    vwap,
    ema5,
    ema20,
)

# =========================
# 委買委賣統計
# =========================

total_bid = sum(
    x["size"]
    for x in bids
)

total_ask = sum(
    x["size"]
    for x in asks
)

buy_strength = round(

    total_bid

    /

    max(
        total_bid + total_ask,
        1,
    )

    * 100

)

sell_strength = 100 - buy_strength

# =========================
# AI 交易判斷
# =========================

action, confidence, reasons = (
    MarketAnalyzer.trading_signal(
        prices,
        price,
        vwap,
        ema5,
        ema20,
        ema60,
        total_bid,
        total_ask,
    )
)

# =========================
# AI 趨勢反轉預測
# =========================

(
    reversal_signal,
    reversal_text,
    reversal_probability,
    reversal_stars,
    reversal_reasons,
) = MarketAnalyzer.reversal_prediction(

    prices,

    price,

    vwap,

    ema5,

    ema20,

    ema60,

    total_bid,

    total_ask,

)

# =========================
# Header
# =========================

st.title(
    f"⚡ {name} ({stock_code})"
)

st.caption(
    now.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)

if market_open:

    st.success(
        "🟢 即時盤中"
    )

else:

    st.warning(
        "🔴 非交易時間"
    )

# =========================
# Price Chart
# =========================

st.subheader("📈 即時價格走勢")

fig = ChartBuilder.build_price_chart(
    prices,
    volumes,
)

st.plotly_chart(
    fig,
    use_container_width=True,
)

# =========================
# 指標
# =========================

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric(
    "現價",
    round(price, 2),
)

c2.metric(
    "VWAP",
    round(vwap, 2),
)

c3.metric(
    "成交量",
    volume,
)

c4.metric(
    "EMA5",
    round(float(ema5), 2),
)

c5.metric(
    "EMA20",
    round(float(ema20), 2),
)

c6.metric(
    "EMA60",
    round(float(ema60), 2),
)

st.divider()

left, center, right = st.columns(3)

# =========================
# AI 判斷
# =========================

with left:

    st.subheader("🤖 AI交易判斷")

    if action == "做多":

        st.success(
            f"🟢 做多 ({confidence}%)"
        )

    elif action == "做空":

        st.error(
            f"🔴 做空 ({confidence}%)"
        )

    else:

        st.warning(
            f"🟡 觀望 ({confidence}%)"
        )

    st.progress(
        confidence / 100
    )

    st.markdown("#### AI判斷依據")

    for reason in reasons:

        st.write(
            f"✅ {reason}"
        )

    st.divider()

    st.markdown("### 🔄 趨勢反轉預測")

    st.metric(
        "反轉機率",
        f"{reversal_probability}%"
    )

    st.progress(
        reversal_probability / 100
    )

    st.write(reversal_stars)

    if reversal_signal == "BUY":

        st.success(
            reversal_text
        )

    elif reversal_signal == "SELL":

        st.error(
            reversal_text
        )

    elif reversal_signal == "WATCH":

        st.warning(
            reversal_text
        )

    else:

        st.info(
            reversal_text
        )

    st.markdown("#### 判斷原因")

    for r in reversal_reasons:

        st.write(
            f"• {r}"
        )

# =========================
# 主力分析
# =========================

with center:

    st.subheader("🏦 主力分析")

    inst_score = MarketAnalyzer.institution_score(
        total_bid,
        total_ask,
    )

    st.metric(
        "主力分數",
        f"{inst_score}/100",
    )

    st.progress(
        inst_score / 100,
    )

    st.metric(
        "委買量",
        total_bid,
    )

    st.metric(
        "委賣量",
        total_ask,
    )

    buy_ratio = round(
        total_bid /
        max(total_bid + total_ask, 1)
        * 100,
        1,
    )

    sell_ratio = round(
        total_ask /
        max(total_bid + total_ask, 1)
        * 100,
        1,
    )

    st.metric(
        "買盤比例",
        f"{buy_ratio}%",
    )

    st.progress(
        buy_ratio / 100,
    )

    st.metric(
        "賣盤比例",
        f"{sell_ratio}%",
    )

    st.progress(
        sell_ratio / 100,
    )

    st.divider()

    if MarketAnalyzer.detect_accumulation(
        total_bid,
        total_ask,
    ):

        st.success(
            "🟢 AI 偵測：主力吸籌中"
        )

    elif MarketAnalyzer.detect_distribution(
        total_bid,
        total_ask,
    ):

        st.error(
            "🔴 AI 偵測：主力出貨中"
        )

    else:

        st.info(
            "🟡 主力尚未明顯表態"
        )

    if MarketAnalyzer.bullish_alignment(
        ema5,
        ema20,
        ema60,
    ):

        st.success(
            "📈 多頭排列"
        )

    elif MarketAnalyzer.bearish_alignment(
        ema5,
        ema20,
        ema60,
    ):

        st.error(
            "📉 空頭排列"
        )

    else:

        st.warning(
            "↔ 均線糾結"
        )

    limit_prob = (
        MarketAnalyzer.limit_up_probability(
            price,
            vwap,
            total_bid,
            total_ask,
        )
    )

    st.metric(
        "漲停機率",
        f"{limit_prob}%",
    )

    st.progress(
        limit_prob / 100,
    )

# =========================
# 綜合評分
# =========================

with right:

    st.subheader("📊 AI綜合評分")

    score = 50

    if price > vwap:
        score += 10

    if ema5 > ema20:
        score += 10

    if ema20 > ema60:
        score += 10

    if total_bid > total_ask:
        score += 20

    if reversal_probability >= 80:
        score += 10

    elif reversal_probability <= 20:
        score -= 10

    score = max(
        0,
        min(score, 100),
    )

    st.metric(
        "AI總分",
        f"{score}/100",
    )

    st.progress(
        score / 100,
    )

    if score >= 90:

        st.success("🚀 強烈做多")

    elif score >= 75:

        st.success("🟢 偏多")

    elif score >= 60:

        st.info("🟡 多方略強")

    elif score >= 40:

        st.warning("⚖️ 震盪整理")

    elif score >= 25:

        st.error("🔴 偏空")

    else:

        st.error("💥 強烈做空")

    st.divider()

    st.metric(
        "目前趨勢",
        trend,
    )

    st.metric(
        "AI信心",
        f"{confidence}%",
    )

    st.metric(
        "反轉機率",
        f"{reversal_probability}%",
    )

st.markdown("---")

# =========================
# 主力分析
# =========================

with center:

    st.subheader("🏦 主力分析")

    inst_score = MarketAnalyzer.institution_score(
        total_bid,
        total_ask,
    )

    st.metric(
        "主力分數",
        f"{inst_score}/100",
    )

    st.progress(
        inst_score / 100,
    )

    st.metric(
        "委買量",
        total_bid,
    )

    st.metric(
        "委賣量",
        total_ask,
    )

    buy_ratio = round(
        total_bid /
        max(total_bid + total_ask, 1)
        * 100,
        1,
    )

    sell_ratio = round(
        total_ask /
        max(total_bid + total_ask, 1)
        * 100,
        1,
    )

    st.metric(
        "買盤比例",
        f"{buy_ratio}%",
    )

    st.progress(
        buy_ratio / 100,
    )

    st.metric(
        "賣盤比例",
        f"{sell_ratio}%",
    )

    st.progress(
        sell_ratio / 100,
    )

    st.divider()

    if MarketAnalyzer.detect_accumulation(
        total_bid,
        total_ask,
    ):

        st.success(
            "🟢 AI 偵測：主力吸籌中"
        )

    elif MarketAnalyzer.detect_distribution(
        total_bid,
        total_ask,
    ):

        st.error(
            "🔴 AI 偵測：主力出貨中"
        )

    else:

        st.info(
            "🟡 主力尚未明顯表態"
        )

    if MarketAnalyzer.bullish_alignment(
        ema5,
        ema20,
        ema60,
    ):

        st.success(
            "📈 多頭排列"
        )

    elif MarketAnalyzer.bearish_alignment(
        ema5,
        ema20,
        ema60,
    ):

        st.error(
            "📉 空頭排列"
        )

    else:

        st.warning(
            "↔ 均線糾結"
        )

    limit_prob = (
        MarketAnalyzer.limit_up_probability(
            price,
            vwap,
            total_bid,
            total_ask,
        )
    )

    st.metric(
        "漲停機率",
        f"{limit_prob}%",
    )

    st.progress(
        limit_prob / 100,
    )

# =========================
# 綜合評分
# =========================

with right:

    st.subheader("📊 AI綜合評分")

    score = 50

    if price > vwap:
        score += 10

    if ema5 > ema20:
        score += 10

    if ema20 > ema60:
        score += 10

    if total_bid > total_ask:
        score += 20

    if reversal_probability >= 80:
        score += 10

    elif reversal_probability <= 20:
        score -= 10

    score = max(
        0,
        min(score, 100),
    )

    st.metric(
        "AI總分",
        f"{score}/100",
    )

    st.progress(
        score / 100,
    )

    if score >= 90:

        st.success("🚀 強烈做多")

    elif score >= 75:

        st.success("🟢 偏多")

    elif score >= 60:

        st.info("🟡 多方略強")

    elif score >= 40:

        st.warning("⚖️ 震盪整理")

    elif score >= 25:

        st.error("🔴 偏空")

    else:

        st.error("💥 強烈做空")

    st.divider()

    st.metric(
        "目前趨勢",
        trend,
    )

    st.metric(
        "AI信心",
        f"{confidence}%",
    )

    st.metric(
        "反轉機率",
        f"{reversal_probability}%",
    )

st.markdown("---")

# =========================
# 大戶成交偵測
# =========================

if (

    market_open

    and

    not is_close

    and

    volume >= big_order_threshold

    and

    trade_serial != st.session_state.last_big_order_serial

):

    st.session_state.last_big_order_serial = trade_serial

    impact_ratio = round(

        volume /

        max(avg_volume, 1),

        2,

    )

    if volume >= 5000:

        level = "🐋 超級主力"

    elif volume >= 1000:

        level = "🔥 主力大單"

    elif volume >= 300:

        level = "📈 法人等級"

    else:

        level = "💰 大戶"

    if total_bid > total_ask:

        direction = "🟢 主力買進"

    elif total_bid < total_ask:

        direction = "🔴 主力賣出"

    else:

        direction = "⚪ 中性"

    st.session_state.big_order_log.insert(

        0,

        {

            "時間": now.strftime("%H:%M:%S"),

            "價格": round(price, 2),

            "成交量": volume,

            "等級": level,

            "方向": direction,

            "影響力": f"{impact_ratio} 倍",

            "來源": data_source,

        },

    )

# =========================
# 主力統計
# =========================

buy_count = sum(

    1

    for row in st.session_state.big_order_log

    if "買進" in row["方向"]

)

sell_count = sum(

    1

    for row in st.session_state.big_order_log

    if "賣出" in row["方向"]

)

net_flow = buy_count - sell_count

c1, c2, c3, c4 = st.columns(4)

c1.metric(

    "大戶門檻",

    f"{big_order_threshold} 張",

)

c2.metric(

    "主力買進",

    buy_count,

)

c3.metric(

    "主力賣出",

    sell_count,

)

c4.metric(

    "淨流向",

    net_flow,

)

st.divider()

# =========================
# 大戶成交紀錄
# =========================

st.subheader("📜 大戶成交紀錄")

if len(st.session_state.big_order_log):

    log_df = pd.DataFrame(

        st.session_state.big_order_log

    )

    st.dataframe(

        log_df,

        use_container_width=True,

        hide_index=True,

        height=320,

    )

else:

    st.info("目前尚未偵測到大戶成交")

# =========================
# 大戶影響力說明
# =========================

impact_df = pd.DataFrame(

    {

        "影響力": [

            "1 倍以下",

            "1~3 倍",

            "3~10 倍",

            "10 倍以上",

        ],

        "代表意義": [

            "一般成交",

            "大戶成交",

            "主力成交",

            "超級主力",

        ],

    }

)

st.subheader("📚 影響力說明")

st.dataframe(

    impact_df,

    use_container_width=True,

    hide_index=True,

)

# =========================
# Best 5
# =========================

st.divider()

st.subheader("📋 最佳五檔")

while len(bids) < 5:

    bids.append(
        {
            "price": 0,
            "size": 0,
        }
    )

while len(asks) < 5:

    asks.append(
        {
            "price": 0,
            "size": 0,
        }
    )

best5_df = pd.DataFrame(

    {

        "委買張數": [

            x["size"]

            for x in bids[:5]

        ],

        "委買價格": [

            x["price"]

            for x in bids[:5]

        ],

        "委賣價格": [

            x["price"]

            for x in asks[:5]

        ],

        "委賣張數": [

            x["size"]

            for x in asks[:5]

        ],

    }

)

st.dataframe(

    best5_df,

    use_container_width=True,

    hide_index=True,

    height=220,

)

# =========================
# 匯出
# =========================

st.divider()

st.subheader("📥 匯出資料")

csv_data = Exporter.export_big_order_log(

    st.session_state.big_order_log

)

left, right = st.columns(2)

with left:

    st.download_button(

        label="📄 匯出大戶成交 CSV",

        data=csv_data,

        file_name=f"{stock_code}_big_order_log.csv",

        mime="text/csv",

        use_container_width=True,

    )

with right:

    st.metric(

        "累積成交筆數",

        len(st.session_state.big_order_log),

    )

# =========================
# Footer
# =========================

st.divider()

footer_left, footer_right = st.columns([3, 1])

with footer_left:

    st.caption(
        "REST PRO v3 | AI Smart Order Flow Analyzer"
    )

    st.caption(
        f"更新時間：{now.strftime('%Y-%m-%d %H:%M:%S')}"
    )

with footer_right:

    if market_open:

        st.success("🟢 LIVE")

    else:

        st.error("🔴 CLOSED")
