import streamlit as st

# =====================================
# 必須放第一行
# =====================================

st.set_page_config(
    page_title="REST PRO",
    page_icon="⚡",
    layout="wide",
)

# =====================================
# Imports
# =====================================

import pandas as pd

from datetime import datetime

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from charts import ChartBuilder
from exporters import Exporter

# =====================================
# Session State
# =====================================

if "price_history" not in st.session_state:
    st.session_state.price_history = []

if "volume_history" not in st.session_state:
    st.session_state.volume_history = []

if "big_order_log" not in st.session_state:
    st.session_state.big_order_log = []

if "tick" not in st.session_state:
    st.session_state.tick = 0

# =====================================
# Sidebar
# =====================================

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
    # 自動大戶門檻
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

        suggest_threshold = max(
            int(avg_volume * 3),
            100
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
            f"目前使用自動門檻：{big_order_threshold}"
        )

    else:

        big_order_threshold = st.number_input(
            "大戶門檻(張)",
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

    if st.button("重置模擬"):

        st.session_state.price_history = []
        st.session_state.volume_history = []
        st.session_state.big_order_log = []
        st.session_state.tick = 0

        st.rerun()

# =====================================
# 資料來源
# =====================================

try:

    if data_source == "真實盤":

        if not api_key:

            st.warning(
                "請輸入 Fugle API Key"
            )

            st.stop()

        provider = FugleProvider(api_key)

        quote = provider.get_quote(
            stock_code
        )

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

# =====================================
# Quote
# =====================================

name = quote["name"]

price = quote["price"]

vwap = quote["vwap"]

volume = quote["last_size"]

bids = quote["bids"]

asks = quote["asks"]

# =====================================
# History
# =====================================

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

# =====================================
# Indicators
# =====================================

ema5 = MarketAnalyzer.calculate_ema(
    prices,
    5
)

ema20 = MarketAnalyzer.calculate_ema(
    prices,
    20
)

ema60 = MarketAnalyzer.calculate_ema(
    prices,
    60
)

trend = MarketAnalyzer.trend(
    price,
    vwap,
    ema5,
    ema20
)

# =====================================
# 主力籌碼
# =====================================

total_bid = sum(
    x["size"]
    for x in bids
)

total_ask = sum(
    x["size"]
    for x in asks
)

# =====================================
# AI判斷
# =====================================

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

# =====================================
# Title
# =====================================

st.title(
    f"⚡ {name}"
)

st.caption(
    f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)

# =====================================
# Chart
# 放最上面
# =====================================

st.subheader(
    "📈 即時價格走勢"
)

fig = ChartBuilder.build_price_chart(
    prices,
    volumes
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =====================================
# Dashboard
# 2 x 3
# =====================================

row1 = st.columns(3)

row1[0].metric(
    "現價",
    round(price, 2)
)

row1[1].metric(
    "VWAP",
    round(vwap, 2)
)

row1[2].metric(
    "趨勢",
    trend
)

row2 = st.columns(3)

row2[0].metric(
    "EMA5",
    round(float(ema5), 2)
)

row2[1].metric(
    "EMA20",
    round(float(ema20), 2)
)

row2[2].metric(
    "EMA60",
    round(float(ema60), 2)
)

# =====================================
# 成交量獨立顯示
# =====================================

st.metric(
    "成交量",
    volume
)

# =====================================
# AI + Best5
# 左右排列
# =====================================

left_col, right_col = st.columns(
    [1, 1]
)

# =====================================
# AI交易判斷
# =====================================

with left_col:

    st.subheader("🤖 AI交易判斷")

    if action == "做多":

        st.success(
            f"🟢 做多優勢｜信心度 {confidence}%"
        )

    elif action == "做空":

        st.error(
            f"🔴 做空優勢｜信心度 {confidence}%"
        )

    else:

        st.warning(
            f"🟡 觀望｜信心度 {confidence}%"
        )

    st.progress(
        confidence / 100
    )

    st.markdown("### 判斷依據")

    for reason in reasons:

        st.write(
            f"✓ {reason}"
        )

    # =====================
    # 買賣壓分析
    # =====================

    st.markdown("---")

    st.markdown(
        "### ⚖️ 買賣力道"
    )

    total_volume = (
        total_bid + total_ask
    )

    if total_volume > 0:

        bid_ratio = (
            total_bid
            /
            total_volume
            * 100
        )

        ask_ratio = (
            total_ask
            /
            total_volume
            * 100
        )

    else:

        bid_ratio = 50
        ask_ratio = 50

    st.write(
        f"買盤力道：{bid_ratio:.1f}%"
    )

    st.progress(
        bid_ratio / 100
    )

    st.write(
        f"賣盤力道：{ask_ratio:.1f}%"
    )

    st.progress(
        ask_ratio / 100
    )

# =====================================
# 最佳五檔
# =====================================

with right_col:

    st.subheader("📋 最佳五檔")

    while len(bids) < 5:

        bids.append({
            "price": 0,
            "size": 0
        })

    while len(asks) < 5:

        asks.append({
            "price": 0,
            "size": 0
        })

    best5_df = pd.DataFrame({

        "買張":

            [
                x["size"]
                for x in bids[:5]
            ],

        "買價":

            [
                x["price"]
                for x in bids[:5]
            ],

        "賣價":

            [
                x["price"]
                for x in asks[:5]
            ],

        "賣張":

            [
                x["size"]
                for x in asks[:5]
            ],
    })

    st.dataframe(
        best5_df,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    st.metric(
        "總買量",
        f"{total_bid:,}"
    )

    st.metric(
        "總賣量",
        f"{total_ask:,}"
    )

    imbalance = total_bid - total_ask

    if imbalance > 0:

        st.success(
            f"買盤優勢 +{imbalance:,}"
        )

    elif imbalance < 0:

        st.error(
            f"賣盤優勢 {imbalance:,}"
        )

    else:

        st.info(
            "買賣均衡"
        )

# =====================================
# 大戶成交紀錄
# =====================================

if volume >= big_order_threshold:

    # =====================
    # 等級判斷
    # =====================

    if volume >= 5000:

        level = "🐋 超級主力"

    elif volume >= 1000:

        level = "🔥 主力大單"

    elif volume >= 300:

        level = "📈 法人等級"

    else:

        level = "💰 大戶"

    # =====================
    # 方向判斷
    # =====================

    if total_bid > total_ask:

        direction = "🟢 主力買進"

    elif total_ask > total_bid:

        direction = "🔴 主力賣出"

    else:

        direction = "⚪ 中性"

    # =====================
    # 寫入紀錄
    # =====================

    st.session_state.big_order_log.insert(
        0,
        {
            "時間":
                datetime.now().strftime(
                    "%H:%M:%S"
                ),

            "價格":
                round(price, 2),

            "張數":
                volume,

            "等級":
                level,

            "方向":
                direction,

            "來源":
                data_source,
        }
    )

# =====================================
# 大戶成交紀錄顯示
# =====================================

st.markdown("---")

st.subheader(
    "📜 大戶成交紀錄"
)

if len(
    st.session_state.big_order_log
) > 0:

    latest = (
        st.session_state.big_order_log[0]
    )

    st.success(
        f"最新大單｜"
        f"{latest['時間']} ｜ "
        f"{latest['方向']} ｜ "
        f"{latest['張數']} 張 ｜ "
        f"{latest['價格']}"
    )

    log_df = pd.DataFrame(
        st.session_state.big_order_log[:50]
    )

    st.dataframe(
        log_df,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info(
        "尚未偵測到大戶成交"
    )

# =====================================
# 主力統計
# =====================================

if len(
    st.session_state.big_order_log
) > 0:

    buy_count = len([
        x
        for x in st.session_state.big_order_log
        if "買進" in x["方向"]
    ])

    sell_count = len([
        x
        for x in st.session_state.big_order_log
        if "賣出" in x["方向"]
    ])

    stat1, stat2 = st.columns(2)

    stat1.metric(
        "主力買進次數",
        buy_count
    )

    stat2.metric(
        "主力賣出次數",
        sell_count
    )

# =====================================
# 匯出
# =====================================

csv_data = (
    Exporter.export_big_order_log(
        st.session_state.big_order_log
    )
)

st.download_button(
    "📥 下載成交紀錄",
    csv_data,
    file_name="big_order_log.csv",
    mime="text/csv",
)

st.caption(
    "REST PRO v2"
)

# =====================================
# AI進階分析
# =====================================

st.markdown("---")

st.markdown("### 🧠 AI主力意圖分析")

bull_score = 0
bear_score = 0

# =====================
# 趨勢
# =====================

if price > ema5:
    bull_score += 10
else:
    bear_score += 10

if ema5 > ema20:
    bull_score += 15
else:
    bear_score += 15

if ema20 > ema60:
    bull_score += 20
else:
    bear_score += 20

# =====================
# VWAP
# =====================

if price > vwap:
    bull_score += 15
else:
    bear_score += 15

# =====================
# 買賣盤
# =====================

if total_bid > total_ask:
    bull_score += 20
else:
    bear_score += 20

# =====================
# 量價
# =====================

avg_volume = (
    sum(volumes[-100:])
    /
    max(
        min(len(volumes), 100),
        1
    )
)

if volume > avg_volume:

    bull_score += 10

# =====================
# 分數正規化
# =====================

total_score = (
    bull_score +
    bear_score
)

if total_score > 0:

    bull_pct = int(
        bull_score /
        total_score *
        100
    )

else:

    bull_pct = 50

bear_pct = 100 - bull_pct

st.metric(
    "多頭優勢",
    f"{bull_pct}%"
)

st.progress(
    bull_pct / 100
)

st.metric(
    "空頭優勢",
    f"{bear_pct}%"
)

st.progress(
    bear_pct / 100
)

# =====================
# 主力意圖
# =====================

if bull_pct >= 70:

    st.success(
        "🔥 主力偏向拉抬"
    )

elif bull_pct >= 60:

    st.success(
        "📈 偏多操作"
    )

elif bull_pct <= 30:

    st.error(
        "⚠️ 主力偏向出貨"
    )

elif bull_pct <= 40:

    st.warning(
        "📉 偏空操作"
    )

else:

    st.info(
        "🤝 多空拉鋸"
    )

# =====================
# 建議進場
# =====================

st.markdown("---")

st.markdown("### 🎯 AI交易計畫")

entry_price = round(
    price,
    2
)

stop_loss = round(
    price * 0.98,
    2
)

take_profit = round(
    price * 1.04,
    2
)

if bull_pct >= 60:

    st.success(
        f"""
建議方向：做多

進場價：{entry_price}

停損價：{stop_loss}

停利價：{take_profit}
"""
    )

elif bull_pct <= 40:

    st.error(
        f"""
建議方向：做空

進場價：{entry_price}

停損價：{take_profit}

停利價：{stop_loss}
"""
    )

else:

    st.warning(
        "目前建議觀望"
    )
