import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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


def _align_series(values, target_len):
    result = []

    for v in values or []:
        result.append(_safe_float(v))

    result = result[-target_len:]

    while len(result) < target_len:
        result.insert(0, None)

    return result


def _render_chart_toolbar(current_price, vwap, ema5, ema20, ema60):

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
            margin-bottom: 8px;
        }}

        .tabs {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .tab {{
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 900;
            color: {SUBTEXT};
            background: rgba(255,255,255,0.035);
            border: 1px solid rgba(255,255,255,0.06);
            white-space: nowrap;
        }}

        .tab-active {{
            color: #ffffff;
            background: rgba(59,130,246,0.20);
            border: 1px solid rgba(59,130,246,0.50);
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

        .periods {{
            display: flex;
            gap: 5px;
            align-items: center;
        }}

        .period {{
            min-width: 34px;
            text-align: center;
            padding: 4px 8px;
            border-radius: 8px;
            font-size: 11.5px;
            font-weight: 900;
            color: {SUBTEXT};
            background: rgba(255,255,255,0.025);
            border: 1px solid rgba(255,255,255,0.05);
        }}

        .period-active {{
            color: #ffffff;
            background: rgba(59,130,246,0.24);
            border-color: rgba(59,130,246,0.55);
        }}

        .info {{
            display: flex;
            gap: 10px;
            color: {SUBTEXT};
            font-size: 11.5px;
            white-space: nowrap;
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
            <div class="tabs">
                <div class="tab tab-active">分時走勢</div>
                <div class="tab">K線走勢</div>
                <div class="tab">多週期分析</div>
            </div>

            <div class="tools">
                <div class="tool">技術指標</div>
                <div class="tool">畫線工具</div>
                <div class="tool">全螢幕</div>
            </div>
        </div>

        <div class="bottom">
            <div class="periods">
                <div class="period period-active">1分</div>
                <div class="period">5分</div>
                <div class="period">15分</div>
                <div class="period">30分</div>
                <div class="period">日</div>
            </div>

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
        height=76,
        scrolling=False,
    )


def render_chart(prices, volumes, vwap_values=None):

    st.markdown("### 📈 分時走勢 / VWAP / MACD")

    if not prices:
        st.caption("等待行情資料中...")
        return

    # =========================
    # 資料整理
    # =========================

    clean_prices = [
        _safe_float(p)
        for p in prices
        if _safe_float(p) > 0
    ]

    if not clean_prices:
        st.caption("尚無有效價格資料")
        return

    clean_prices = clean_prices[-160:]

    clean_volumes = [
        _to_lot(v)
        for v in volumes[-len(clean_prices):]
    ]

    while len(clean_volumes) < len(clean_prices):
        clean_volumes.insert(0, 0)

    n = len(clean_prices)

    clean_vwap = _align_series(
        vwap_values,
        n,
    )

    x = []

    for i in range(n):
        if n <= 1:
            x.append("最新")
        else:
            x.append(f"T-{n - i - 1}" if i < n - 1 else "最新")

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
        current_price=current_price,
        vwap=current_vwap,
        ema5=ema5[-1] if ema5 else current_price,
        ema20=ema20[-1] if ema20 else current_price,
        ema60=ema60[-1] if ema60 else current_price,
    )

    macd_line, signal_line, hist = _macd(clean_prices)

    # =========================
    # 顏色
    # 台股：上漲紅，下跌綠
    # =========================

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

    # =========================
    # 建立三層圖表
    # =========================

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.58, 0.22, 0.20],
        vertical_spacing=0.025,
    )

    # =========================
    # 價格線
    # =========================

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
            line=dict(
                color="#facc15",
                width=1.3,
            ),
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
            line=dict(
                color="#fb7185",
                width=1.3,
            ),
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
            line=dict(
                color="#a855f7",
                width=1.3,
            ),
        ),
        row=1,
        col=1,
    )

    # =========================
    # VWAP 線
    # =========================

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

    # =========================
    # 成交量
    # =========================

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

    # =========================
    # MACD
    # =========================

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
            line=dict(
                color="#38bdf8",
                width=1.4,
            ),
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
            line=dict(
                color="#f97316",
                width=1.2,
            ),
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

    # =========================
    # Y 軸範圍
    # =========================

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

    # =========================
    # 資料不足提示
    # =========================

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

    # =========================
    # Layout
    # =========================

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
        key="main_price_volume_vwap_macd_chart",
    )
