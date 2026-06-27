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


def render_chip_panel(bids, asks, big_order_log, decision):

    bid_total = _sum_size(bids)
    ask_total = _sum_size(asks)

    ratio = bid_total / max(ask_total, 1)

    action = decision.get("action", "WAIT")
    bias = _safe_float(decision.get("bias", 0))

    if action == "BUY" or bias >= 4:
        main_status = "主力偏多"
        main_color = UP_COLOR
        chip_desc = "多方條件較完整，觀察是否有連續買盤承接。"

    elif action == "SELL" or bias <= -4:
        main_status = "主力偏空"
        main_color = DOWN_COLOR
        chip_desc = "空方壓力較大，留意反彈無力後再壓回。"

    else:
        main_status = "籌碼觀望"
        main_color = WAIT_COLOR
        chip_desc = "籌碼尚未明顯表態，等待大單或量能確認。"

    if ratio >= 1.5:
        depth_status = "委買強"
        depth_color = UP_COLOR

    elif ratio <= 0.65:
        depth_status = "委賣強"
        depth_color = DOWN_COLOR

    else:
        depth_status = "均衡"
        depth_color = WAIT_COLOR

    latest_title = "尚無主力大單"
    latest_text = "等待大單訊號出現"
    latest_color = SUBTEXT
    latest_icon = "🐋"

    if big_order_log:

        latest = big_order_log[-1]
        direction = latest.get("direction", "UNKNOWN")

        if direction == "BUY":
            latest_color = UP_COLOR
            latest_title = "最新偏多大單"
            latest_icon = "🔴"

        elif direction == "SELL":
            latest_color = DOWN_COLOR
            latest_title = "最新偏空大單"
            latest_icon = "🟢"

        else:
            latest_color = WAIT_COLOR
            latest_title = "最新大單方向不明"
            latest_icon = "🟡"

        latest_text = (
            f'{latest.get("direction_text", "-")}｜'
            f'{latest.get("volume_lot", "-")} 張｜'
            f'強度 {latest.get("strength", "-")}'
        )

    risk_text = "等待確認"
    risk_color = WAIT_COLOR

    if action == "BUY":
        risk_text = "追高風險"
        risk_color = WAIT_COLOR

    elif action == "SELL":
        risk_text = "反彈風險"
        risk_color = WAIT_COLOR

    if abs(bias) >= 6:
        risk_text = "方向明確"
        risk_color = main_color

    st.markdown("### 🧩 主力籌碼分析")

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
            align-items: flex-start;
            margin-bottom: 10px;
        }}

        .label {{
            color: {SUBTEXT};
            font-size: 12px;
            margin-bottom: 4px;
        }}

        .main {{
            color: {main_color};
            font-size: 20px;
            font-weight: 900;
        }}

        .desc {{
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.35;
            margin-top: 4px;
        }}

        .tag {{
            border: 1px solid {main_color};
            color: {main_color};
            border-radius: 999px;
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 900;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 7px;
            margin-top: 10px;
        }}

        .box {{
            background: rgba(255,255,255,0.035);
            border-radius: 10px;
            padding: 8px 6px;
            text-align: center;
        }}

        .box-label {{
            color: {SUBTEXT};
            font-size: 11px;
            margin-bottom: 4px;
        }}

        .box-value {{
            font-size: 14px;
            font-weight: 900;
        }}

        .latest {{
            margin-top: 10px;
            padding: 9px;
            border-radius: 10px;
            background: rgba(255,255,255,0.035);
            border-left: 4px solid {latest_color};
        }}

        .latest-title {{
            color: {latest_color};
            font-size: 13px;
            font-weight: 900;
            margin-bottom: 4px;
        }}

        .latest-text {{
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.35;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .note {{
            margin-top: 9px;
            padding-top: 8px;
            border-top: 1px solid rgba(255,255,255,0.08);
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.35;
        }}
    </style>
</head>

<body>
    <div class="card">

        <div class="top">
            <div>
                <div class="label">主力方向</div>
                <div class="main">{main_status}</div>
                <div class="desc">{chip_desc}</div>
            </div>

            <div class="tag">{depth_status}</div>
        </div>

        <div class="grid">

            <div class="box">
                <div class="box-label">委買力道</div>
                <div class="box-value" style="color:{UP_COLOR};">{_fmt(bid_total)}</div>
            </div>

            <div class="box">
                <div class="box-label">籌碼差距</div>
                <div class="box-value" style="color:{main_color};">{bias:.0f}</div>
            </div>

            <div class="box">
                <div class="box-label">風險提醒</div>
                <div class="box-value" style="color:{risk_color};">{risk_text}</div>
            </div>

        </div>

        <div class="latest">
            <div class="latest-title">{latest_icon} {latest_title}</div>
            <div class="latest-text">{escape(str(latest_text))}</div>
        </div>

        <div class="note">
            五檔詳細數字已集中在左下「委買委賣 / 多空力道」，此區只保留主力籌碼結論。
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=260,
        scrolling=False,
    )
