import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from ui.multi_period_panel import render_multi_period_analysis
from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    TEXT,
    SUBTEXT,
    CARD_BG,
    CARD_BORDER,
)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _clamp(value, low=0, high=100):
    return max(low, min(high, value))


def _ema(values, span):
    nums = [_safe_float(v) for v in values]

    if not nums:
        return []

    alpha = 2 / (span + 1)
    result = [nums[0]]

    for v in nums[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])

    return result


def _macd(values):
    nums = [_safe_float(v) for v in values]

    if not nums:
        return [], [], []

    ema12 = _ema(nums, 12)
    ema26 = _ema(nums, 26)

    macd_line = []

    for i in range(len(nums)):
        macd_line.append(ema12[i] - ema26[i])

    signal_line = _ema(macd_line, 9)

    hist = []

    for i in range(len(nums)):
        hist.append(macd_line[i] - signal_line[i])

    return macd_line, signal_line, hist


def _to_lot(volume):
    volume = _safe_float(volume)

    if volume >= 1000:
        return round(volume / 1000, 2)

    return round(volume, 2)


def _to_datetime(value):
    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _period_minutes(period):
    mapping = {
        "1分": 1,
        "5分": 5,
        "15分": 15,
        "30分": 30,
        "日": 390,
    }

    return mapping.get(period, 1)


def _bucket_time(dt, minutes):
    if dt is None:
        return None

    if minutes >= 390:
        return dt.replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )

    minute = (dt.minute // minutes) * minutes

    return dt.replace(
        minute=minute,
        second=0,
        microsecond=0,
    )


def _prepare_ticks(prices, volumes, vwaps, times):
    clean = []

    for i, price in enumerate(prices or []):
        p = _safe_float(price)

        if p <= 0:
            continue

        v = _safe_float(volumes[i]) if i < len(volumes or []) else 0
        w = _safe_float(vwaps[i]) if i < len(vwaps or []) else p
        t = _to_datetime(times[i]) if i < len(times or []) else None

        clean.append(
            {
                "price": p,
                "volume": v,
                "vwap": w if w > 0 else p,
                "time": t,
            }
        )

    return clean


def _aggregate_line(prices, volumes, vwaps, times, period):
    """
    分時線圖資料。
    1分：原始即時點
    5/15/30分：用區間最後價
    日：日內全部資料線圖
    """

    clean = _prepare_ticks(prices, volumes, vwaps, times)

    if not clean:
        return [], [], [], []

    if period in ["1分", "日"]:
        agg_prices = [item["price"] for item in clean]
        agg_volumes = [item["volume"] for item in clean]
        agg_vwaps = [item["vwap"] for item in clean]
        labels = []

        for idx, item in enumerate(clean):
            if item["time"] is not None:
                if period == "日":
                    labels.append(item["time"].strftime("%H:%M"))
                else:
                    labels.append(item["time"].strftime("%H:%M:%S"))
            else:
                labels.append(
                    f"T-{len(clean) - idx - 1}"
                    if idx < len(clean) - 1
                    else "最新"
                )

        return agg_prices, agg_volumes, agg_vwaps, labels

    minutes = _period_minutes(period)
    buckets = {}
    fallback_index = 0

    for item in clean:
        key = _bucket_time(item["time"], minutes)

        if key is None:
            key = f"bucket_{fallback_index // minutes}"
            fallback_index += 1

        if key not in buckets:
            buckets[key] = {
                "prices": [],
                "volumes": [],
                "vwaps": [],
                "label": key,
            }

        buckets[key]["prices"].append(item["price"])
        buckets[key]["volumes"].append(item["volume"])
        buckets[key]["vwaps"].append(item["vwap"])

    agg_prices = []
    agg_volumes = []
    agg_vwaps = []
    labels = []

    for key in sorted(buckets.keys(), key=lambda x: str(x)):
        group = buckets[key]

        agg_prices.append(group["prices"][-1])
        agg_volumes.append(sum(group["volumes"]))

        valid_vwaps = [
            _safe_float(v)
            for v in group["vwaps"]
            if _safe_float(v) > 0
        ]

        if valid_vwaps:
            agg_vwaps.append(sum(valid_vwaps) / len(valid_vwaps))
        else:
            agg_vwaps.append(group["prices"][-1])

        if isinstance(group["label"], datetime):
            labels.append(group["label"].strftime("%H:%M"))
        else:
            labels.append(str(group["label"]))

    return agg_prices, agg_volumes, agg_vwaps, labels


def _aggregate_ohlc(prices, volumes, vwaps, times, period):
    """
    K線資料。
    open = 區間第一筆
    high = 區間最高
    low = 區間最低
    close = 區間最後一筆
    volume = 區間量加總
    vwap = 區間 vwap 平均
    """

    clean = _prepare_ticks(prices, volumes, vwaps, times)

    if not clean:
        return {
            "x": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
            "vwap": [],
        }

    minutes = _period_minutes(period)
    buckets = {}
    fallback_index = 0

    for item in clean:
        key = _bucket_time(item["time"], minutes)

        if key is None:
            key = f"bucket_{fallback_index // max(minutes, 1)}"
            fallback_index += 1

        if key not in buckets:
            buckets[key] = {
                "prices": [],
                "volumes": [],
                "vwaps": [],
                "label": key,
            }

        buckets[key]["prices"].append(item["price"])
        buckets[key]["volumes"].append(item["volume"])
        buckets[key]["vwaps"].append(item["vwap"])

    x = []
    opens = []
    highs = []
    lows = []
    closes = []
    vols = []
    k_vwaps = []

    for key in sorted(buckets.keys(), key=lambda x: str(x)):
        group = buckets[key]
        ps = group["prices"]

        if not ps:
            continue

        opens.append(ps[0])
        highs.append(max(ps))
        lows.append(min(ps))
        closes.append(ps[-1])
        vols.append(sum(group["volumes"]))

        valid_vwaps = [
            _safe_float(v)
            for v in group["vwaps"]
            if _safe_float(v) > 0
        ]

        if valid_vwaps:
            k_vwaps.append(sum(valid_vwaps) / len(valid_vwaps))
        else:
            k_vwaps.append(ps[-1])

        if isinstance(group["label"], datetime):
            if period == "日":
                x.append(group["label"].strftime("%m/%d"))
            else:
                x.append(group["label"].strftime("%H:%M"))
        else:
            x.append(str(group["label"]))

    return {
        "x": x,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": vols,
        "vwap": k_vwaps,
    }


def _render_chart_toolbar(
    mode,
    period,
    current_price,
    vwap,
    ema5,
    ema20,
    ema60,
    data_points,
):

    current_price = _safe_float(current_price)
    vwap = _safe_float(vwap)
    ema5 = _safe_float(ema5)
    ema20 = _safe_float(ema20)
    ema60 = _safe_float(ema60)

    if current_price >= vwap:
        price_state = "站上 VWAP"
        price_color = UP_COLOR
    else:
        price_state = "跌破 VWAP"
        price_color = DOWN_COLOR

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: Arial, "Microsoft JhengHei", sans-serif;
            color: {TEXT};
            overflow: hidden;
        }}

        .wrap {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 13px;
            padding: 8px 10px;
            box-sizing: border-box;
            width: 100%;
        }}

        .top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            margin-bottom: 7px;
        }}

        .mode {{
            display: flex;
            align-items: center;
            gap: 7px;
            color: {TEXT};
            font-size: 12px;
            font-weight: 900;
            white-space: nowrap;
        }}

        .pill {{
            color: #ffffff;
            background: rgba(59,130,246,0.22);
            border: 1px solid rgba(59,130,246,0.55);
            border-radius: 999px;
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 900;
        }}

        .tools {{
            display: flex;
            align-items: center;
            gap: 7px;
            color: {SUBTEXT};
            font-size: 11.5px;
            white-space: nowrap;
        }}

        .tool {{
            padding: 4px 7px;
            border-radius: 8px;
            background: rgba(255,255,255,0.035);
        }}

        .bottom {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }}

        .info {{
            display: flex;
            gap: 10px;
            color: {SUBTEXT};
            font-size: 11.5px;
            white-space: nowrap;
            overflow: hidden;
        }}

        .info b {{
            color: {TEXT};
        }}

        .state {{
            color: {price_color};
            font-weight: 900;
        }}

        @media (max-width: 900px) {{
            .top,
            .bottom {{
                align-items: flex-start;
                flex-direction: column;
            }}

            .tools,
            .info {{
                flex-wrap: wrap;
                white-space: normal;
            }}
        }}
    </style>
</head>

<body>
    <div class="wrap">

        <div class="top">
            <div class="mode">
                <span>{mode}</span>
                <span class="pill">{period}</span>
                <span class="pill">資料 {data_points}</span>
            </div>

            <div class="tools">
                <div class="tool">技術指標</div>
                <div class="tool">畫線工具</div>
                <div class="tool">全螢幕</div>
            </div>
        </div>

        <div class="bottom">
            <div class="info">
                <span>Price <b>{current_price:.2f}</b></span>
                <span>VWAP <b>{vwap:.2f}</b></span>
                <span>EMA5 <b>{ema5:.2f}</b></span>
                <span>EMA20 <b>{ema20:.2f}</b></span>
                <span>EMA60 <b>{ema60:.2f}</b></span>
                <span class="state">{price_state}</span>
            </div>
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=65,
        scrolling=False,
    )


def _select_control(label, options, default, key):
    """
    優先使用 Streamlit segmented_control。
    如果環境不支援，就自動退回 radio。
    """

    if hasattr(st, "segmented_control"):
        value = st.segmented_control(
            label,
            options,
            default=default,
            key=key,
            label_visibility="collapsed",
        )

        if value is None:
            return default

        return value

    return st.radio(
        label,
        options,
        index=options.index(default),
        horizontal=True,
        label_visibility="collapsed",
        key=key,
    )


def _render_period_selector():

    st.markdown(
        """
<style>
.chart-control-title {
    color: #9ca3af;
    font-size: 11px;
    font-weight: 800;
    margin-bottom: 3px;
}

div[data-testid="stHorizontalBlock"] {
    align-items: center;
}

div[data-testid="stRadio"] label {
    font-size: 11px !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] {
    gap: 6px;
}

div[data-testid="stRadio"] div[role="radiogroup"] label {
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 999px;
    padding: 4px 10px;
}
</style>
""",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([0.92, 1.08], gap="small")

    with col1:
        st.markdown(
            '<div class="chart-control-title">圖表模式</div>',
            unsafe_allow_html=True,
        )

        mode = _select_control(
            label="圖表模式",
            options=["分時走勢", "K線走勢", "多週期分析"],
            default="分時走勢",
            key="chart_mode_selector",
        )

    with col2:
        st.markdown(
            '<div class="chart-control-title">週期</div>',
            unsafe_allow_html=True,
        )

        period = _select_control(
            label="週期",
            options=["1分", "5分", "15分", "30分", "日"],
            default="1分",
            key="chart_period_selector",
        )

    return mode, period

def _add_common_layout(fig, chart_key):
    fig.update_layout(
        height=390,
        margin=dict(
            l=12,
            r=12,
            t=18,
            b=8,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0b0f16",
        font=dict(
            color=TEXT,
            size=10,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(
                size=10,
                color=TEXT,
            ),
        ),
        hovermode="x unified",
        bargap=0.18,
        xaxis_rangeslider_visible=False,
    )

    for row in [1, 2, 3]:
        fig.update_xaxes(
            showgrid=False,
            zeroline=False,
            showline=False,
            tickfont=dict(
                color=SUBTEXT,
                size=9,
            ),
            row=row,
            col=1,
        )

        fig.update_yaxes(
            gridcolor="rgba(255,255,255,0.07)",
            zeroline=False,
            showline=False,
            tickfont=dict(
                color=TEXT,
                size=9,
            ),
            row=row,
            col=1,
        )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=chart_key,
    )


def _render_line_chart(clean_prices, clean_volumes, clean_vwap, x, mode, period):
    n = len(clean_prices)

    current_price = clean_prices[-1]
    prev_price = clean_prices[-2] if len(clean_prices) >= 2 else current_price

    price_color = UP_COLOR if current_price >= prev_price else DOWN_COLOR

    ema5 = _ema(clean_prices, 5)
    ema20 = _ema(clean_prices, 20)
    ema60 = _ema(clean_prices, 60)

    current_vwap = current_price

    valid_vwap = [
        v
        for v in clean_vwap
        if v is not None and _safe_float(v) > 0
    ]

    if valid_vwap:
        current_vwap = valid_vwap[-1]

    _render_chart_toolbar(
        mode=mode,
        period=period,
        current_price=current_price,
        vwap=current_vwap,
        ema5=ema5[-1] if ema5 else current_price,
        ema20=ema20[-1] if ema20 else current_price,
        ema60=ema60[-1] if ema60 else current_price,
        data_points=n,
    )

    macd_line, signal_line, hist = _macd(clean_prices)

    volume_colors = []

    for i, p in enumerate(clean_prices):
        if i == 0:
            volume_colors.append(price_color)
        else:
            if p >= clean_prices[i - 1]:
                volume_colors.append(UP_COLOR)
            else:
                volume_colors.append(DOWN_COLOR)

    hist_colors = []

    for h in hist:
        if h >= 0:
            hist_colors.append(UP_COLOR)
        else:
            hist_colors.append(DOWN_COLOR)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.58, 0.22, 0.20],
        vertical_spacing=0.025,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=clean_prices,
            mode="lines+markers" if n <= 8 else "lines",
            name="Price",
            line=dict(
                color=price_color,
                width=2.4,
            ),
            marker=dict(
                size=6,
                color=price_color,
            ),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema5,
            mode="lines",
            name="EMA5",
            line=dict(color="#facc15", width=1.3),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema20,
            mode="lines",
            name="EMA20",
            line=dict(color="#fb7185", width=1.3),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema60,
            mode="lines",
            name="EMA60",
            line=dict(color="#a855f7", width=1.3),
        ),
        row=1,
        col=1,
    )

    if clean_vwap and any(v is not None and v > 0 for v in clean_vwap):
        fig.add_trace(
            go.Scatter(
                x=x,
                y=clean_vwap,
                mode="lines",
                name="VWAP",
                connectgaps=True,
                line=dict(
                    color="#22c55e",
                    width=1.8,
                    dash="dot",
                ),
            ),
            row=1,
            col=1,
        )

    fig.add_hline(
        y=current_price,
        line=dict(
            color="#00e5ff",
            width=1.1,
            dash="dot",
        ),
        row=1,
        col=1,
    )

    fig.add_annotation(
        x=x[-1],
        y=current_price,
        text=f"{current_price:.2f}",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-30,
        bgcolor=price_color,
        bordercolor=price_color,
        font=dict(
            color="#ffffff",
            size=10,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=x,
            y=clean_volumes,
            name="Volume",
            marker=dict(
                color=volume_colors,
                opacity=0.72,
            ),
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=x,
            y=hist,
            name="MACD Hist",
            marker=dict(
                color=hist_colors,
                opacity=0.75,
            ),
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=macd_line,
            mode="lines",
            name="MACD",
            line=dict(color="#38bdf8", width=1.4),
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=signal_line,
            mode="lines",
            name="Signal",
            line=dict(color="#f97316", width=1.2),
        ),
        row=3,
        col=1,
    )

    fig.add_hline(
        y=0,
        line=dict(
            color="rgba(255,255,255,0.18)",
            width=1,
        ),
        row=3,
        col=1,
    )

    price_candidates = clean_prices[:]

    for v in clean_vwap:
        if v is not None and v > 0:
            price_candidates.append(v)

    high = max(price_candidates)
    low = min(price_candidates)

    price_padding = max(
        (high - low) * 0.35,
        current_price * 0.001,
    )

    fig.update_yaxes(
        range=[
            low - price_padding,
            high + price_padding,
        ],
        row=1,
        col=1,
    )

    max_volume = max(clean_volumes) if clean_volumes else 1

    fig.update_yaxes(
        range=[
            0,
            max(max_volume * 1.35, 1),
        ],
        row=2,
        col=1,
    )

    if hist:
        macd_high = max(
            max(macd_line),
            max(signal_line),
            max(hist),
        )
        macd_low = min(
            min(macd_line),
            min(signal_line),
            min(hist),
        )

        macd_padding = max(
            (macd_high - macd_low) * 0.35,
            0.01,
        )

        fig.update_yaxes(
            range=[
                macd_low - macd_padding,
                macd_high + macd_padding,
            ],
            row=3,
            col=1,
        )

    if n < 8:
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.62,
            text="資料累積中",
            showarrow=False,
            font=dict(
                color="rgba(255,255,255,0.35)",
                size=18,
            ),
        )

    _add_common_layout(
        fig,
        chart_key=f"line_chart_{mode}_{period}",
    )


def _render_k_chart(ohlc, mode, period):
    x = ohlc["x"]
    opens = ohlc["open"]
    highs = ohlc["high"]
    lows = ohlc["low"]
    closes = ohlc["close"]
    volumes = [_to_lot(v) for v in ohlc["volume"]]
    vwaps = ohlc["vwap"]

    if not closes:
        st.caption("尚無 K 線資料")
        return

    n = len(closes)

    current_price = closes[-1]
    current_vwap = vwaps[-1] if vwaps else current_price

    ema5 = _ema(closes, 5)
    ema20 = _ema(closes, 20)
    ema60 = _ema(closes, 60)

    _render_chart_toolbar(
        mode=mode,
        period=period,
        current_price=current_price,
        vwap=current_vwap,
        ema5=ema5[-1] if ema5 else current_price,
        ema20=ema20[-1] if ema20 else current_price,
        ema60=ema60[-1] if ema60 else current_price,
        data_points=n,
    )

    macd_line, signal_line, hist = _macd(closes)

    candle_colors = []

    for i in range(n):
        if closes[i] >= opens[i]:
            candle_colors.append(UP_COLOR)
        else:
            candle_colors.append(DOWN_COLOR)

    hist_colors = []

    for h in hist:
        if h >= 0:
            hist_colors.append(UP_COLOR)
        else:
            hist_colors.append(DOWN_COLOR)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.58, 0.22, 0.20],
        vertical_spacing=0.025,
    )

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name="K",
            increasing=dict(
                line=dict(color=UP_COLOR, width=1.2),
                fillcolor=UP_COLOR,
            ),
            decreasing=dict(
                line=dict(color=DOWN_COLOR, width=1.2),
                fillcolor=DOWN_COLOR,
            ),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema5,
            mode="lines",
            name="EMA5",
            line=dict(color="#facc15", width=1.2),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema20,
            mode="lines",
            name="EMA20",
            line=dict(color="#fb7185", width=1.2),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema60,
            mode="lines",
            name="EMA60",
            line=dict(color="#a855f7", width=1.2),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=vwaps,
            mode="lines",
            name="VWAP",
            line=dict(
                color="#22c55e",
                width=1.7,
                dash="dot",
            ),
        ),
        row=1,
        col=1,
    )

    fig.add_hline(
        y=current_price,
        line=dict(
            color="#00e5ff",
            width=1.1,
            dash="dot",
        ),
        row=1,
        col=1,
    )

    fig.add_annotation(
        x=x[-1],
        y=current_price,
        text=f"{current_price:.2f}",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-30,
        bgcolor=UP_COLOR if closes[-1] >= opens[-1] else DOWN_COLOR,
        bordercolor=UP_COLOR if closes[-1] >= opens[-1] else DOWN_COLOR,
        font=dict(
            color="#ffffff",
            size=10,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=x,
            y=volumes,
            name="Volume",
            marker=dict(
                color=candle_colors,
                opacity=0.72,
            ),
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=x,
            y=hist,
            name="MACD Hist",
            marker=dict(
                color=hist_colors,
                opacity=0.75,
            ),
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=macd_line,
            mode="lines",
            name="MACD",
            line=dict(color="#38bdf8", width=1.4),
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=signal_line,
            mode="lines",
            name="Signal",
            line=dict(color="#f97316", width=1.2),
        ),
        row=3,
        col=1,
    )

    fig.add_hline(
        y=0,
        line=dict(
            color="rgba(255,255,255,0.18)",
            width=1,
        ),
        row=3,
        col=1,
    )

    price_candidates = highs + lows + vwaps

    high = max(price_candidates)
    low = min(price_candidates)

    price_padding = max(
        (high - low) * 0.35,
        current_price * 0.001,
    )

    fig.update_yaxes(
        range=[
            low - price_padding,
            high + price_padding,
        ],
        row=1,
        col=1,
    )

    max_volume = max(volumes) if volumes else 1

    fig.update_yaxes(
        range=[
            0,
            max(max_volume * 1.35, 1),
        ],
        row=2,
        col=1,
    )

    if hist:
        macd_high = max(
            max(macd_line),
            max(signal_line),
            max(hist),
        )
        macd_low = min(
            min(macd_line),
            min(signal_line),
            min(hist),
        )

        macd_padding = max(
            (macd_high - macd_low) * 0.35,
            0.01,
        )

        fig.update_yaxes(
            range=[
                macd_low - macd_padding,
                macd_high + macd_padding,
            ],
            row=3,
            col=1,
        )

    if n < 3:
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.62,
            text="K線資料累積中",
            showarrow=False,
            font=dict(
                color="rgba(255,255,255,0.35)",
                size=18,
            ),
        )

    _add_common_layout(
        fig,
        chart_key=f"k_chart_{mode}_{period}",
    )


def render_chart(prices, volumes, vwap_values=None, time_values=None):

    st.markdown("### 📈 分時 / K線 / VWAP / MACD")

    if not prices:
        st.caption("等待行情資料中...")
        return

    mode, period = _render_period_selector()

    if mode == "K線走勢":
        ohlc = _aggregate_ohlc(
            prices=prices,
            volumes=volumes,
            vwaps=vwap_values or [],
            times=time_values or [],
            period=period,
        )

        _render_k_chart(
            ohlc=ohlc,
            mode=mode,
            period=period,
        )

        return

    if mode == "多週期分析":
        render_multi_period_analysis(
            prices=prices,
            volumes=volumes,
            vwap_values=vwap_values or [],
            time_values=time_values or [],
        )
        return

    clean_prices, clean_volumes, clean_vwap, x = _aggregate_line(
        prices=prices,
        volumes=volumes,
        vwaps=vwap_values or [],
        times=time_values or [],
        period=period,
    )

    if not clean_prices:
        st.caption("尚無有效價格資料")
        return

    clean_prices = clean_prices[-160:]
    clean_volumes = clean_volumes[-160:]
    clean_vwap = clean_vwap[-160:]
    x = x[-160:]

    clean_volumes = [
        _to_lot(v)
        for v in clean_volumes
    ]

    _render_line_chart(
        clean_prices=clean_prices,
        clean_volumes=clean_volumes,
        clean_vwap=clean_vwap,
        x=x,
        mode=mode,
        period=period,
    )
