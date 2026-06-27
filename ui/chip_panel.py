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


def render_chip_panel(bids, asks, big_order_log, decision):

    action = decision.get("action", "WAIT")
    bias = _safe_float(decision.get("bias", 0))
    score = _safe_float(decision.get("score", 0))
    fake_signal = decision.get("fake_signal", "NONE")

    # =========================
    # 主力方向結論
    # =========================

    if action == "BUY" or bias >= 4:
        main_status = "主力偏多"
        main_color = UP_COLOR
        chip_desc = "多方條件較完整，觀察是否有連續買盤承接。"

    elif action == "SELL" or bias <= -4:
        main_status = "主力偏空"
        main_color = DOWN_COLOR
        chip_desc = "空方壓力較大，反彈不過壓力區容易再壓回。"

    else:
        main_status = "籌碼觀望"
        main_color = WAIT_COLOR
        chip_desc = "籌碼尚未明顯表態，等待大單或量能確認。"

    # =========================
    # 假突破風險
    # =========================

    if fake_signal == "FAKE_BREAKOUT":
        risk_title = "假突破風險"
        risk_color = WAIT_COLOR
        risk_desc = "疑似突破後量能不足，避免追多。"

    elif fake_signal == "FAKE_BREAKDOWN":
        risk_title = "假跌破風險"
        risk_color = WAIT_COLOR
        risk_desc = "疑似跌破後殺盤不乾脆，避免追空。"

    elif score >= 75:
        risk_title = "方向較明確"
        risk_color = main_color
        risk_desc = "Decision Score 偏高，但仍需等待進場區。"

    else:
        risk_title = "等待確認"
        risk_color = WAIT_COLOR
        risk_desc = "目前不適合只依單一訊號進場。"

    # =========================
    # 最新主力大單
    # =========================

    latest_title = "尚無主力大單"
    latest_text = "等待大單訊號出現。"
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
            f'{latest.get("time", "-")}｜'
            f'{latest.get("direction_text", "-")}｜'
            f'{latest.get("volume_lot", "-")} 張｜'
            f'{latest.get("strength", "-")}'
        )

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
            font-size: 21px;
            font-weight: 900;
        }}

        .desc {{
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.4;
            margin-top: 5px;
        }}

        .tag {{
            border: 1px solid {main_color};
            color: {main_color};
            border-radius: 999px;
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 900;
            white-space: nowrap;
        }}

        .section {{
            margin-top: 10px;
            padding: 9px;
            border-radius: 11px;
            background: rgba(255,255,255,0.035);
            border-left: 4px solid {latest_color};
        }}

        .section-title {{
            color: {latest_color};
            font-size: 13px;
            font-weight: 900;
            margin-bottom: 4px;
        }}

        .section-text {{
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.35;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .risk {{
            margin-top: 9px;
            padding: 9px;
            border-radius: 11px;
            background: rgba(255,255,255,0.035);
            border-left: 4px solid {risk_color};
        }}

        .risk-title {{
            color: {risk_color};
            font-size: 13px;
            font-weight: 900;
            margin-bottom: 4px;
        }}

        .risk-text {{
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.35;
        }}

        .note {{
            margin-top: 9px;
            padding-top: 8px;
            border-top: 1px solid rgba(255,255,255,0.08);
            color: {SUBTEXT};
            font-size: 11px;
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

            <div class="tag">Score {int(score)}</div>
        </div>

        <div class="section">
            <div class="section-title">{latest_icon} {latest_title}</div>
            <div class="section-text">{escape(str(latest_text))}</div>
        </div>

        <div class="risk">
            <div class="risk-title">⚠️ {risk_title}</div>
            <div class="risk-text">{risk_desc}</div>
        </div>

        <div class="note">
            五檔、委買、委賣、買賣比已集中在左下「委買委賣 / 多空力道」區，右側只保留籌碼結論。
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=205,
        scrolling=False,
    )
