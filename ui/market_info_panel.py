import streamlit as st
import streamlit.components.v1 as components
from html import escape

from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    CARD_BG,
    CARD_BORDER,
    TEXT,
    SUBTEXT,
)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _sum_size(levels):
    total = 0

    for item in levels or []:
        total += _safe_float(item.get("size", 0))

    return total


def _fmt(value):
    value = _safe_float(value)

    if value >= 1000:
        return f"{value / 1000:.1f}K"

    if abs(value - round(value)) < 0.01:
        return str(int(round(value)))

    return f"{value:.1f}"


def render_market_info_panel(bids, asks, big_order_log):

    bid_total = _sum_size(bids)
    ask_total = _sum_size(asks)

    ratio = bid_total / max(ask_total, 1)

    if ratio >= 1.5:
        status = "主力買盤強"
        status_color = UP_COLOR
        desc = "委買明顯大於委賣"

    elif ratio >= 1.15:
        status = "買盤偏強"
        status_color = UP_COLOR
        desc = "買方略佔優勢"

    elif ratio <= 0.6:
        status = "主力賣壓重"
        status_color = DOWN_COLOR
        desc = "委賣明顯大於委買"

    elif ratio <= 0.85:
        status = "賣壓偏強"
        status_color = DOWN_COLOR
        desc = "賣方略佔優勢"

    else:
        status = "籌碼平衡"
        status_color = WAIT_COLOR
        desc = "買賣雙方拉鋸"

    total = max(bid_total + ask_total, 1)

    bid_pct = int(bid_total / total * 100)
    ask_pct = int(ask_total / total * 100)

    latest_html = ""

    if big_order_log:

        latest = big_order_log[-1]

        direction = latest.get("direction", "UNKNOWN")
        direction_text = escape(str(latest.get("direction_text", "-")))
        strength = escape(str(latest.get("strength", "-")))
        time_text = escape(str(latest.get("time", "-")))
        price = escape(str(latest.get("price", "-")))
        volume_lot = escape(str(latest.get("volume_lot", "-")))

        if direction == "BUY":
            latest_color = UP_COLOR
            latest_icon = "🔴"
            latest_title = "主力偏多大單"

        elif direction == "SELL":
            latest_color = DOWN_COLOR
            latest_icon = "🟢"
            latest_title = "主力偏空大單"

        else:
            latest_color = WAIT_COLOR
            latest_icon = "🟡"
            latest_title = "方向不明大單"

        latest_html = f"""
        <div class="latest-box">
            <div class="latest-top">
                <div class="latest-title" style="color:{latest_color};">
                    {latest_icon} {latest_title}
                </div>
                <div class="time">{time_text}</div>
            </div>

            <div class="latest-main">
                <span style="color:{latest_color};">{volume_lot} 張</span>
                <span>{direction_text}</span>
            </div>

            <div class="latest-sub">
                價格 {price}｜強度 {strength}
            </div>
        </div>
        """

    else:

        latest_html = f"""
        <div class="latest-box">
            <div class="latest-top">
                <div class="latest-title" style="color:{SUBTEXT};">
                    🐋 尚無主力大單
                </div>
                <div class="time">-</div>
            </div>

            <div class="latest-main">
                <span style="color:{SUBTEXT};">等待大單出現</span>
            </div>

            <div class="latest-sub">
                系統會依成交量門檻自動偵測。
            </div>
        </div>
        """

    rows_html = ""

    if big_order_log:

        for item in big_order_log[-3:][::-1]:

            direction = item.get("direction", "UNKNOWN")

            if direction == "BUY":
                row_color = UP_COLOR
                icon = "🔴"

            elif direction == "SELL":
                row_color = DOWN_COLOR
                icon = "🟢"

            else:
                row_color = WAIT_COLOR
                icon = "🟡"

            rows_html += f"""
            <div class="log-row">
                <div style="color:{row_color};font-weight:900;">
                    {icon} {escape(str(item.get("direction_text", "-")))}
                </div>
                <div>{escape(str(item.get("price", "-")))}</div>
                <div>{escape(str(item.get("volume_lot", "-")))} 張</div>
            </div>
            """

    else:

        rows_html = f"""
        <div class="empty-log">
            目前尚未累積大單紀錄
        </div>
        """

    st.markdown("### 📡 主力資訊")

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

        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 14px;
            padding: 12px;
            box-sizing: border-box;
            width: 100%;
        }}

        .top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .label {{
            color: {SUBTEXT};
            font-size: 12px;
            font-weight: 700;
        }}

        .status {{
            color: {status_color};
            font-size: 18px;
            font-weight: 900;
        }}

        .desc {{
            color: {SUBTEXT};
            font-size: 11.5px;
            margin-top: 3px;
        }}

        .force {{
            margin-top: 10px;
        }}

        .force-row {{
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            margin-bottom: 5px;
            color: {SUBTEXT};
        }}

        .bar {{
            width: 100%;
            height: 12px;
            background: rgba(255,255,255,0.10);
            border-radius: 999px;
            overflow: hidden;
            display: flex;
        }}

        .bid-bar {{
            width: {bid_pct}%;
            height: 100%;
            background: {UP_COLOR};
        }}

        .ask-bar {{
            width: {ask_pct}%;
            height: 100%;
            background: {DOWN_COLOR};
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 7px;
            margin-top: 10px;
        }}

        .box {{
            background: rgba(255,255,255,0.035);
            border-radius: 10px;
            padding: 7px;
            text-align: center;
        }}

        .box-label {{
            color: {SUBTEXT};
            font-size: 11px;
            margin-bottom: 3px;
        }}

        .box-value {{
            color: {TEXT};
            font-size: 14px;
            font-weight: 900;
        }}

        .latest-box {{
            margin-top: 11px;
            background: rgba(255,255,255,0.035);
            border-radius: 12px;
            padding: 10px;
            border-left: 4px solid {status_color};
        }}

        .latest-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}

        .latest-title {{
            font-size: 13px;
            font-weight: 900;
        }}

        .time {{
            color: {SUBTEXT};
            font-size: 11px;
        }}

        .latest-main {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            font-weight: 900;
            margin-bottom: 4px;
        }}

        .latest-sub {{
            color: {SUBTEXT};
            font-size: 11.5px;
        }}

        .log {{
            margin-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 8px;
        }}

        .log-title {{
            color: {SUBTEXT};
            font-size: 11.5px;
            margin-bottom: 5px;
        }}

        .log-row {{
            display: grid;
            grid-template-columns: 1.5fr 0.8fr 0.8fr;
            gap: 6px;
            font-size: 11.5px;
            color: {TEXT};
            padding: 4px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}

        .empty-log {{
            color: {SUBTEXT};
            font-size: 11.5px;
            padding: 6px 0;
        }}
    </style>
</head>

<body>
    <div class="card">

        <div class="top">
            <div>
                <div class="label">主力方向</div>
                <div class="desc">{desc}</div>
            </div>

            <div class="status">{status}</div>
        </div>

        <div class="force">
            <div class="force-row">
                <div>買盤 {_fmt(bid_total)}</div>
                <div>賣盤 {_fmt(ask_total)}</div>
            </div>

            <div class="bar">
                <div class="bid-bar"></div>
                <div class="ask-bar"></div>
            </div>
        </div>

        <div class="summary">
            <div class="box">
                <div class="box-label">買方占比</div>
                <div class="box-value" style="color:{UP_COLOR};">{bid_pct}%</div>
            </div>

            <div class="box">
                <div class="box-label">買賣比</div>
                <div class="box-value" style="color:{status_color};">{ratio:.2f}</div>
            </div>

            <div class="box">
                <div class="box-label">賣方占比</div>
                <div class="box-value" style="color:{DOWN_COLOR};">{ask_pct}%</div>
            </div>
        </div>

        {latest_html}

        <div class="log">
            <div class="log-title">最近大單</div>
            {rows_html}
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=330,
        scrolling=False,
    )
