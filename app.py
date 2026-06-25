import streamlit as st
import pandas as pd

from datetime import datetime, timedelta

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
    page_title="REST PRO v2",
    page_icon="⚡",
    layout="wide",
)



# =========================
# 台灣時間
# =========================

taipei_time = (
    datetime.utcnow()
    + timedelta(hours=8)
)

# =========================
# Session State
# =========================

if "price_history" not in st.session_state:
    st.session_state.price_history = []

if "volume_history" not in st.session_state:
    st.session_state.volume_history = []

if "big_order_log" not in st.session_state:
    st.session_state.big_order_log = []

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
            "情境模擬"
        ]
    )

    stock_code = st.text_input(
        "股票代號",
        "2330"
    )

    api_key = st.text_input(
        "Fugle API Key",
        type="password"
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
        ]
    )

    # =====================
    # 大戶門檻
    # =====================

    auto_threshold = st.checkbox(
        "自動大戶門檻",
        value=True
    )

    if len(st.session_state.volume_history) > 0:

        avg_volume = (
            sum(
                st.session_state.volume_history[-100:]
            )
            /
            min(
                len(st.session_state.volume_history),
                100
            )
        )

        suggest_threshold = int(
            avg_volume * 3
        )

        st.info(
            f"📊 最近100筆平均量：{avg_volume:.0f} 張\n\n"
            f"建議大戶門檻：{suggest_threshold} 張"
        )

    else:

        suggest_threshold = 100

    if auto_threshold:

        big_order_threshold = (
            suggest_threshold
        )

        st.success(
            f"目前使用自動門檻："
            f"{big_order_threshold} 張"
        )

    else:

        big_order_threshold = st.number_input(
            "大戶門檻(張)",
            min_value=10,
            max_value=10000,
            value=100,
            step=10
        )

    sim_minutes = st.slider(
        "模擬時間(分鐘)",
        2,
        60,
        10
    )

    if st.button("重置模擬"):

        st.session_state.price_history = []
        st.session_state.volume_history = []
        st.session_state.big_order_log = []
        st.session_state.tick = 0

        st.rerun()
# =========================
# Data Provider
# =========================

try:

    if data_source == "真實盤":

        if not api_key:

            st.warning(
                "請輸入 Fugle API Key"
            )

            st.stop()

        provider = FugleProvider(
            api_key
        )

        quote = provider.get_quote(
            stock_code
        )

        st.sidebar.write(quote)

    else:

        engine = SimulationEngine(
            mode=sim_mode,
            base_price=100
        )

        quote = engine.generate(
            st.session_state.tick,
            sim_minutes * 60
        )

        st.session_state.tick += 1

except Exception as e:

    st.error(
        f"資料取得失敗：{e}"
    )

    st.stop()

# =========================
# Quote
# =========================

name = quote["name"]

price = quote["price"]

vwap = quote["vwap"]

volume = quote["last_size"]

bids = quote["bids"]

asks = quote["asks"]

is_close = quote.get(
    "is_close",
    False
)

# 永遠刷新頁面
refresh_count = st_autorefresh(
    interval=2000,
    key="refresh"
)

if not is_close:

    st.sidebar.success(
        "🟢 即時更新中"
    )

else:

    st.sidebar.warning(
        "🔴 已收盤"
    )

# =========================
# History
# =========================

if not is_close:

    if (
        len(st.session_state.price_history) == 0
        or
        st.session_state.price_history[-1] != price
    ):

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

ema5 = (
    MarketAnalyzer.calculate_ema(
        prices,
        5
    )
)

ema20 = (
    MarketAnalyzer.calculate_ema(
        prices,
        20
    )
)

ema60 = (
    MarketAnalyzer.calculate_ema(
        prices,
        60
    )
)

trend = (
    MarketAnalyzer.trend(
        price,
        vwap,
        ema5,
        ema20
    )
)

# =========================
# 主力統計
# =========================

total_bid = sum(
    x["size"]
    for x in bids
)

total_ask = sum(
    x["size"]
    for x in asks
)

buy_strength = (
    round(
        total_bid
        /
        max(
            total_bid + total_ask,
            1
        )
        * 100
    )
)

sell_strength = (
    100 - buy_strength
)
# =========================
# Header
# =========================

st.title(
    f"⚡ {name} {stock_code}"
)

st.caption(
    f"🕒 現在時間："
    f"{taipei_time.strftime('%Y-%m-%d %H:%M:%S')}"
)

# =========================
# Chart
# =========================

st.subheader(
    "📈 價格走勢"
)

fig = ChartBuilder.build_price_chart(
    prices,
    volumes
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =========================
# 指標區
# 2 x 3
# =========================

st.markdown("---")

row1 = st.columns(3)

with row1[0]:

    st.metric(
        "現價",
        round(price, 2)
    )

with row1[1]:

    st.metric(
        "VWAP",
        round(vwap, 2)
    )

with row1[2]:

    st.metric(
        "成交量",
        volume
    )

row2 = st.columns(3)

with row2[0]:

    st.metric(
        "EMA5",
        round(
            float(ema5),
            2
        )
    )

with row2[1]:

    st.metric(
        "EMA20",
        round(
            float(ema20),
            2
        )
    )

with row2[2]:

    st.metric(
        "EMA60",
        round(
            float(ema60),
            2
        )
    )

st.metric(
    "趨勢",
    trend
)

st.markdown("---")

# =========================
# AI交易判斷
# =========================

action, confidence, reasons = (
    MarketAnalyzer.trading_signal(
        price,
        vwap,
        ema5,
        ema20,
        ema60,
        total_bid,
        total_ask,
    )
)

left, center, right = st.columns(3)

# =========================
# AI判斷
# =========================

with left:

    st.subheader(
        "🤖 AI交易判斷"
    )

    if action == "做多":

        st.success(
            f"🟢 做多優勢 | 信心度 {confidence}%"
        )

    elif action == "做空":

        st.error(
            f"🔴 做空優勢 | 信心度 {confidence}%"
        )

    else:

        st.warning(
            f"🟡 觀望 | 信心度 {confidence}%"
        )

    st.progress(
        confidence / 100
    )

    st.markdown("### 判斷依據")

    for reason in reasons:

        st.write(
            f"✓ {reason}"
        )

# =========================
# 主力分析
# =========================

inst_score = (
    MarketAnalyzer.institution_score(
        total_bid,
        total_ask
    )
)

st.subheader("🏦 主力分析")

c1, c2, c3 = st.columns(3)

c1.metric(
    "主力分數",
    f"{inst_score}"
)

c2.metric(
    "委買量",
    total_bid
)

c3.metric(
    "委賣量",
    total_ask
)

if MarketAnalyzer.detect_accumulation(
    total_bid,
    total_ask,
):
    st.success(
        "🟢 偵測到主力吸籌"
    )

if MarketAnalyzer.detect_distribution(
    total_bid,
    total_ask,
):
    st.error(
        "🔴 偵測到主力出貨"
    )

if MarketAnalyzer.bullish_alignment(
    ema5,
    ema20,
    ema60,
):
    st.success(
        "📈 多頭排列"
    )

if MarketAnalyzer.bearish_alignment(
    ema5,
    ema20,
    ema60,
):
    st.error(
        "📉 空頭排列"
    )

prob = (
    MarketAnalyzer.limit_up_probability(
        price,
        vwap,
        total_bid,
        total_ask,
    )
)

st.progress(prob)

st.write(
    f"🚀 漲停機率預估：{prob}%"
)

# =========================
# 買賣力道
# =========================

with center:

    st.subheader(
        "🎯 主力買賣力道"
    )

    st.metric(
        "買盤比例",
        f"{buy_strength}%"
    )

    st.progress(
        buy_strength / 100
    )

    st.metric(
        "賣盤比例",
        f"{sell_strength}%"
    )

    st.progress(
        sell_strength / 100
    )

# =========================
# 主力分數
# =========================

with right:

    st.subheader(
        "📊 主力分數"
    )

    score = 50

    if price > vwap:
        score += 10

    if ema5 > ema20:
        score += 10

    if ema20 > ema60:
        score += 10

    if total_bid > total_ask:
        score += 20

    score = max(
        0,
        min(score, 100)
    )

    st.metric(
        "主力分數",
        f"{score}/100"
    )

    st.progress(
        score / 100
    )

    if score >= 80:

        st.success(
            "強勢多頭"
        )

    elif score >= 60:

        st.info(
            "偏多"
        )

    elif score >= 40:

        st.warning(
            "震盪整理"
        )

    else:

        st.error(
            "偏空"
        )

st.markdown("---")

# =========================
# 大戶成交偵測
# =========================

if volume >= big_order_threshold:

    impact_ratio = round(
        volume
        /
        max(avg_volume, 1),
        2
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

    elif total_ask > total_bid:

        direction = "🔴 主力賣出"

    else:

        direction = "⚪ 中性"

    st.session_state.big_order_log.insert(
        0,
        {
            "時間": datetime.now().strftime(
                "%H:%M:%S"
            ),
            "價格": round(
                price,
                2
            ),
            "張數": volume,
            "等級": level,
            "方向": direction,
            "影響力": f"{impact_ratio}倍",
            "來源": data_source,
        }
    )

# =========================
# 主力統計
# =========================

buy_count = 0
sell_count = 0

for row in st.session_state.big_order_log:

    if "買進" in row["方向"]:

        buy_count += 1

    elif "賣出" in row["方向"]:

        sell_count += 1

net_flow = (
    buy_count
    -
    sell_count
)

# =========================
# 主力統計區
# =========================

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "大戶門檻",
        f"{big_order_threshold} 張"
    )

with c2:

    st.metric(
        "主力買進次數",
        buy_count
    )

with c3:

    st.metric(
        "主力賣出次數",
        sell_count
    )

with c4:

    st.metric(
        "淨差額",
        net_flow
    )

st.markdown("---")

# =========================
# 大戶成交紀錄
# =========================

st.subheader(
    "📜 大戶成交紀錄"
)

if len(
    st.session_state.big_order_log
) > 0:

    log_df = pd.DataFrame(
        st.session_state.big_order_log[:50]
    )

    st.dataframe(
        log_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "尚未偵測到大戶成交"
    )

# =========================
# 影響力說明
# =========================

st.subheader(
    "📚 大戶成交影響力說明"
)

impact_df = pd.DataFrame(
    {
        "影響力倍數": [
            "0 ~ 1倍",
            "1 ~ 3倍",
            "3 ~ 10倍",
            "10倍以上"
        ],
        "代表意義": [
            "一般成交量",
            "明顯大單",
            "主力大單",
            "超級主力單"
        ]
    }
)

st.dataframe(
    impact_df,
    use_container_width=True,
    hide_index=True
)

# =========================
# Best 5
# =========================

st.markdown("---")

st.subheader(
    "📋 最佳五檔"
)

while len(bids) < 5:

    bids.append(
        {
            "price": 0,
            "size": 0
        }
    )

while len(asks) < 5:

    asks.append(
        {
            "price": 0,
            "size": 0
        }
    )

best5_df = pd.DataFrame(
    {
        "買張":
            [x["size"] for x in bids[:5]],

        "買價":
            [x["price"] for x in bids[:5]],

        "賣價":
            [x["price"] for x in asks[:5]],

        "賣張":
            [x["size"] for x in asks[:5]],
    }
)

st.dataframe(
    best5_df,
    use_container_width=True,
    hide_index=True
)

# =========================
# Download
# =========================

st.markdown("---")

st.subheader(
    "📥 匯出資料"
)

csv_data = (
    Exporter.export_big_order_log(
        st.session_state.big_order_log
    )
)

st.download_button(
    label="📥 下載大戶成交紀錄",
    data=csv_data,
    file_name="big_order_log.csv",
    mime="text/csv"
)

# =========================
# Footer
# =========================

st.markdown("---")

st.caption(
    "REST PRO v2 | AI Order Flow Analyzer"
)

st.caption(
    f"更新時間："
    f"{taipei_time.strftime('%Y-%m-%d %H:%M:%S')}"
)
