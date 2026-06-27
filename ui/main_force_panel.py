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


def _safe_int(value, default=0):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _clamp(value, low=0, high=100):
    return max(low, min(high, value))


def _sum_size(levels):
    total = 0

    for item in levels or []:
        total += _safe_float(item.get("size", 0))

    return total


def _row_html(title, status, desc, pct, color):
    pct = _clamp(_safe_int(pct), 0, 100)

    return f"""
    <div class="force-row">
        <div class="row-top">
            <div class="row-title">{escape(str(title))}</div>
            <div class="row-status" style="color:{color};">{escape(str(status))}</div>
        </div>

        <div class="bar-bg">
            <div class="bar-fill" style="width:{pct}%; background:{color};"></div>
        </div>

        <div class="row-desc">{escape(str(desc))}</div>
    </div>
    """


def render_main_force_panel(bids, asks, big_order_log, decision):

    bid_total = _sum_size(bids)
    ask_total = _sum_size(asks)

    depth_ratio = bid_total / max(ask_total, 1)

    action = decision.get("action", "WAIT")
    score = _safe_int(decision.get("score", 0))
    bias = _safe_float(decision.get("bias", 0))
    rebound = _safe_int(decision.get("rebound", 0))
    fake_signal = decision.get("fake_signal", "NONE")

    # =========================
    # 主力動向
    # =========================

    if action == "BUY" or bias >= 4:
        force_status = "主力偏多"
        force_color = UP_COLOR
        force_desc = "多方條件較完整，觀察是否持續承接。"
        force_pct = max(score, 55)

    elif action == "SELL" or bias <= -4:
        force_status = "主力偏空"
        force_color = DOWN_COLOR
        force_desc = "空方壓力較大，反彈不過容易再壓回。"
        force_pct = max(score, 55)

    else:
        force_status = "主力觀望"
        force_color = WAIT_COLOR
        force_desc = "多空尚未明顯表態。"
        force_pct = max(score, 35)

    # =========================
    # 五檔結構
    # =========================

    if depth_ratio >= 1.35:
        depth_status = "買盤支撐"
        depth_color = UP_COLOR
        depth_desc = "委買支撐較強。"
        depth_pct = min(95, 55 + (depth_ratio - 1) * 30)

    elif depth_ratio <= 0.74:
        depth_status = "賣壓較重"
        depth_color = DOWN_COLOR
        depth_desc = "委賣壓力較重。"
        depth_pct = min(95, 55 + (1 - depth_ratio) * 30)

    else:
        depth_status = "結構均衡"
        depth_color = WAIT_COLOR
        depth_desc = "買賣雙方拉鋸。"
        depth_pct = 50

    # =========================
    # 大單方向
    # =========================

    if big_order_log:

        latest = big_order_log[-1]
        direction = latest.get("direction", "UNKNOWN")

        if direction == "BUY":
            big_status = "大單偏多"
            big_color = UP_COLOR
            big_desc = f'{latest.get("direction_text", "-")}｜{latest.get("volume_lot", "-")} 張'
            big_pct = 75

        elif direction == "SELL":
            big_status = "大單偏空"
            big_color = DOWN_COLOR
            big_desc = f'{latest.get("direction_text", "-")}｜{latest.get("volume_lot", "-")} 張'
            big_pct = 75

        else:
            big_status = "方向不明"
            big_color = WAIT_COLOR
            big_desc = "出現大單，但方向尚未確認。"
            big_pct = 50

    else:

        big_status = "等待大單"
        big_color = WAIT_COLOR
        big_desc = "尚未偵測到主力大單。"
        big_pct = 35

    # =========================
    # 防守 / 風險
    # =========================

    if fake_signal == "FAKE_BREAKOUT":
        risk_status = "假突破風險"
        risk_color = WAIT_COLOR
        risk_desc = "突破後量能不足，避免追多。"
        risk_pct = 70

    elif fake_signal == "FAKE_BREAKDOWN":
        risk_status = "假跌破風險"
        risk_color = WAIT_COLOR
        risk_desc = "跌破後殺盤不乾脆，避免追空。"
        risk_pct = 70

    elif rebound >= 60:
        risk_status = "反彈條件"
        risk_color = UP_COLOR
        risk_desc = "反彈條件較完整。"
        risk_pct = rebound

    elif rebound <= 35:
        risk_status = "反彈偏弱"
        risk_color = DOWN_COLOR
        risk_desc = "反彈條件不足。"
        risk_pct = 100 - rebound

    else:
        risk_status = "風險監控"
        risk_color = WAIT_COLOR
        risk_desc = "等待更明確的量價訊號。"
        risk_pct = 50

    rows_html = ""
    rows_html += _row_html("主力動向", force_status, force_desc, force_pct, force_color)
    rows_html += _row_html("五檔結構", depth_status, depth_desc, depth_pct, depth_color)
    rows_html += _row_html("大單方向", big_status, big_desc, big_pct, big_color)
    rows_html += _row_html("防守動向", risk_status, risk_desc, risk_pct, risk_color)

    st.markdown("### 📡 主力動向分析")

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
            padding: 11px;
            box-sizing: border-box;
            width: 100%;
        }}

        .head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .head-left {{
            color: {SUBTEXT};
            font-size: 11.5px;
        }}

        .head-right {{
            color: {force_color};
            font-size: 18px;
            font-weight: 900;
        }}

        .force-row {{
            margin-top: 8px;
            padding-top: 7px;
            border-top: 1px solid rgba(255,255,255,0.06);
        }}

        .row-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }}

        .row-title {{
            color: {SUBTEXT};
            font-size: 11.5px;
            font-weight: 800;
        }}

        .row-status {{
            font-size: 12.5px;
            font-weight: 900;
        }}

        .bar-bg {{
            width: 100%;
            height: 9px;
            border-radius: 999px;
            background: rgba(255,255,255,0.10);
            overflow: hidden;
        }}

        .bar-fill {{
            height: 100%;
            border-radius: 999px;
        }}

        .row-desc {{
            color: {SUBTEXT};
            font-size: 10.8px;
            line-height: 1.35;
            margin-top: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
    </style>
</head>

<body>
    <div class="card">

        <div class="head">
            <div class="head-left">綜合主力、五檔、大單、防守狀態</div>
            <div class="head-right">{force_status}</div>
        </div>

        {rows_html}

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=245,
        scrolling=False,
    )
