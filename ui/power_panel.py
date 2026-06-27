import streamlit as st
import streamlit.components.v1 as components

from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    CARD_BG,
    CARD_BORDER,
    TEXT,
    SUBTEXT,
)


def _to_int(value, default=0):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def render_power_panel(decision):

    long_score = _to_int(decision.get("long_score", 0))
    short_score = _to_int(decision.get("short_score", 0))
    bias = _to_int(decision.get("bias", long_score - short_score))

    total = max(long_score + short_score, 1)

    long_pct = int(long_score / total * 100)
    short_pct = int(short_score / total * 100)

    if bias >= 4:
        status = "多方優勢"
        status_color = UP_COLOR

    elif bias <= -4:
        status = "空方優勢"
        status_color = DOWN_COLOR

    else:
        status = "多空拉鋸"
        status_color = WAIT_COLOR

    st.markdown("### ⚔️ 多空力道")

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
            }}

            .card {{
                background: {CARD_BG};
                border: 1px solid {CARD_BORDER};
                border-radius: 14px;
                padding: 14px;
                box-sizing: border-box;
                width: 100%;
            }}

            .row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}

            .label {{
                font-size: 13px;
                color: {SUBTEXT};
            }}

            .status {{
                font-size: 18px;
                font-weight: 800;
                color: {status_color};
            }}

            .score-row {{
                margin-top: 12px;
                margin-bottom: 6px;
                display: flex;
                justify-content: space-between;
                font-size: 13px;
                font-weight: 700;
            }}

            .long {{
                color: {UP_COLOR};
            }}

            .short {{
                color: {DOWN_COLOR};
            }}

            .bar {{
                width: 100%;
                height: 12px;
                background: #263241;
                border-radius: 99px;
                overflow: hidden;
                display: flex;
            }}

            .long-bar {{
                width: {long_pct}%;
                background: {UP_COLOR};
            }}

            .short-bar {{
                width: {short_pct}%;
                background: {DOWN_COLOR};
            }}

            .pct-row {{
                margin-top: 8px;
                display: flex;
                justify-content: space-between;
                color: {SUBTEXT};
                font-size: 12px;
            }}

            .bias {{
                margin-top: 12px;
                padding-top: 10px;
                border-top: 1px solid rgba(255,255,255,0.08);
                font-size: 13px;
                color: {TEXT};
            }}
        </style>
    </head>

    <body>
        <div class="card">

            <div class="row">
                <div class="label">目前狀態</div>
                <div class="status">{status}</div>
            </div>

            <div class="score-row">
                <div class="long">多方 {long_score}</div>
                <div class="short">空方 {short_score}</div>
            </div>

            <div class="bar">
                <div class="long-bar"></div>
                <div class="short-bar"></div>
            </div>

            <div class="pct-row">
                <div>多方占比 {long_pct}%</div>
                <div>空方占比 {short_pct}%</div>
            </div>

            <div class="bias">
                多空差距：<b>{bias}</b>
            </div>

        </div>
    </body>
    </html>
    """

    components.html(
        html,
        height=170,
        scrolling=False,
    )
