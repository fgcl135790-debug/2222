import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    TEXT,
    SUBTEXT,
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


def _to_lot(volume):
    volume = _safe_float(volume)

    if volume >= 1000:
        return round(volume / 1000, 2)

    return round(volume, 2)


def render_chart(prices, volumes):

    st.markdown("### 📈 分時趨勢")

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

    clean_prices = clean_prices[-120:]

    clean_volumes = [
        _to_lot(v)
        for v in volumes[-len(clean_prices):]
    ]

    while len(clean_volumes) < len(clean_prices):
        clean_volumes.insert(0, 0)

    n = len(clean_prices)

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

    # =========================
    # 成交量顏色
    # 台股：漲紅、跌綠
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

    # =========================
    # 建立圖表
    # =========================

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        vertical_spacing=0.03,
    )

    # 價格線
    fig.add_trace(
        go.Scatter(
            x=x,
            y=clean_prices,
            mode="lines+markers" if n <= 6 else "lines",
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

    # EMA5
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema5,
            mode="lines",
            name="EMA5",
            line=dict(
                color="#facc15",
                width=1.4,
            ),
        ),
        row=1,
        col=1,
    )

    # EMA20
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema20,
            mode="lines",
            name="EMA20",
            line=dict(
                color="#fb7185",
                width=1.4,
            ),
        ),
        row=1,
        col=1,
    )

    # EMA60
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema60,
            mode="lines",
            name="EMA60",
            line=dict(
                color="#a855f7",
                width=1.4,
            ),
        ),
        row=1,
        col=1,
    )

    # 現價水平線
    fig.add_hline(
        y=current_price,
        line=dict(
            color="#00e5ff",
            width=1.2,
            dash="dot",
        ),
        row=1,
        col=1,
    )

    # 現價標籤
    fig.add_annotation(
        x=x[-1],
        y=current_price,
        text=f"{current_price:.2f}",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-32,
        bgcolor=price_color,
        bordercolor=price_color,
        font=dict(
            color="#ffffff",
            size=11,
        ),
        row=1,
        col=1,
    )

    # 成交量
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
    # Y 軸範圍
    # =========================

    high = max(clean_prices)
    low = min(clean_prices)

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

    # =========================
    # 資料不足提示
    # =========================

    if n < 8:
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.58,
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
        height=385,
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
            size=11,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(
                size=11,
                color=TEXT,
            ),
        ),
        hovermode="x unified",
        bargap=0.18,
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        tickfont=dict(
            color=SUBTEXT,
            size=10,
        ),
        row=1,
        col=1,
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        tickfont=dict(
            color=SUBTEXT,
            size=10,
        ),
        row=2,
        col=1,
    )

    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.08)",
        zeroline=False,
        showline=False,
        tickfont=dict(
            color=TEXT,
            size=10,
        ),
        row=1,
        col=1,
    )

    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.06)",
        zeroline=False,
        showline=False,
        tickfont=dict(
            color=TEXT,
            size=10,
        ),
        row=2,
        col=1,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="main_price_chart",
    )
