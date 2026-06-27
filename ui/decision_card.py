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


def _safe_int(value, default=50):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _fmt(value):
    if value is None:
        return "-"

    try:
        if isinstance(value, (int, float)):
            return f"{value:.2f}"
    except Exception:
        pass

    return str(value)


def render_decision_card(decision):

    action = decision.get("action", "WAIT")
    score = _safe_int(decision.get("score", 50))
    score = max(0, min(100, score))

    entry = escape(_fmt(decision.get("entry", "-")))
    stop = escape(_fmt(decision.get("stop_loss", "-")))
    target = escape(_fmt(decision.get("take_profit", "-")))
    rr = escape(_fmt(decision.get("rr", "-")))

    reasons = decision.get("reasons", [])

    # =========================
    # 台股顏色
    # =========================

    if action == "BUY":
        color = UP_COLOR
        title = "可當沖做多"
        subtitle = "多方策略"
        badge = "BUY"
        action_text = "偏多觀察"

    elif action == "SELL":
        color = DOWN_COLOR
        title = "可當沖做空"
        subtitle = "空方策略"
        badge = "SELL"
        action_text = "偏空觀察"

    else:
        color = WAIT_COLOR
        title = "等待進場"
        subtitle = "觀望策略"
        badge = "WAIT"
        action_text = "等待確認"

    title = escape(title)
    subtitle = escape(subtitle)
    badge = escape(badge)
    action_text = escape(action_text)

    # =========================
    # 半圓 Gauge
    # =========================

    arc_len = 188.5
    dash_offset = arc_len * (1 - score / 100)

    st.markdown("### 🎯 交易決策 (V7.5)")

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
            background: linear-gradient(135deg, rgba(17,24,39,0.98), rgba(9,14,24,0.98));
            border: 1px solid {CARD_BORDER};
            border-radius: 16px;
            padding: 15px;
            box-sizing: border-box;
            width: 100%;
            box-shadow: inset 0 0 18px rgba(255,255,255,0.025);
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
            margin-bottom: 5px;
        }}

        .title {{
            color: {color};
            font-size: 28px;
            font-weight: 900;
            line-height: 1.05;
        }}

        .badge {{
            color: {color};
            border: 1px solid {color};
            background: rgba(255,255,255,0.035);
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 900;
        }}

        .main {{
            display: grid;
            grid-template-columns: 1.05fr 0.95fr;
            gap: 12px;
            align-items: center;
        }}

        .info {{
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 10px;
        }}

        .row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            font-size: 13px;
        }}

        .row .k {{
            color: {SUBTEXT};
            font-weight: 700;
        }}

        .row .v {{
            color: {TEXT};
            font-weight: 900;
        }}

        .rr {{
            color: {color} !important;
        }}

        .gauge-box {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}

        .score-text {{
            color: {SUBTEXT};
            font-size: 11px;
            margin-top: -6px;
        }}

        .hint {{
            margin-top: 8px;
            padding: 8px 10px;
            border-radius: 10px;
            background: rgba(255,255,255,0.035);
            border-left: 4px solid {color};
            font-size: 12px;
            color: {SUBTEXT};
            line-height: 1.45;
        }}

        @media (max-width: 700px) {{
            .main {{
                grid-template-columns: 1fr;
            }}

            .title {{
                font-size: 24px;
            }}
        }}
    </style>
</head>

<body>
    <div class="card">

        <div class="top">
            <div>
                <div class="label">建議策略</div>
                <div class="title">{title}</div>
            </div>

            <div class="badge">{badge}</div>
        </div>

        <div class="main">

            <div class="info">

                <div class="row">
                    <div class="k">進場區間</div>
                    <div class="v">{entry}</div>
                </div>

                <div class="row">
                    <div class="k">停損價位</div>
                    <div class="v">{stop}</div>
                </div>

                <div class="row">
                    <div class="k">停利目標</div>
                    <div class="v">{target}</div>
                </div>

                <div class="row">
                    <div class="k">風險報酬比</div>
                    <div class="v rr">{rr}</div>
                </div>

            </div>

            <div class="gauge-box">

                <svg width="150" height="95" viewBox="0 0 160 95">

                    <path
                        d="M 20 80 A 60 60 0 0 1 140 80"
                        fill="none"
                        stroke="rgba(255,255,255,0.12)"
                        stroke-width="15"
                        stroke-linecap="round"
                    />

                    <path
                        d="M 20 80 A 60 60 0 0 1 140 80"
                        fill="none"
                        stroke="{color}"
                        stroke-width="15"
                        stroke-linecap="round"
                        stroke-dasharray="{arc_len}"
                        stroke-dashoffset="{dash_offset}"
                    />

                    <text
                        x="80"
                        y="70"
                        text-anchor="middle"
                        font-size="31"
                        font-weight="900"
                        fill="#ffffff"
                    >
                        {score}
                    </text>

                    <text
                        x="103"
                        y="70"
                        font-size="10"
                        font-weight="700"
                        fill="{SUBTEXT}"
                    >
                        /100
                    </text>

                    <text
                        x="80"
                        y="25"
                        text-anchor="middle"
                        font-size="10"
                        font-weight="700"
                        fill="{SUBTEXT}"
                    >
                        綜合評分
                    </text>

                </svg>

                <div class="score-text">{subtitle}｜{action_text}</div>

            </div>

        </div>

        <div class="hint">
            系統根據 AI、VWAP、EMA、RSI、MACD、五檔力道與假突破條件產生此決策。
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=238,
        scrolling=False,
    )

    # =========================
    # AI 判斷依據
    # =========================

    st.markdown("#### AI 判斷依據")

    if not reasons:
        st.caption("目前無分析內容")
        return

    show_reasons = reasons[:8]

    for r in show_reasons:
        safe_reason = escape(str(r))

        st.markdown(
            f"""
            <div style="
                display:flex;
                gap:7px;
                align-items:flex-start;
                font-size:13px;
                line-height:1.55;
                margin-bottom:4px;
                color:{TEXT};
            ">
                <span style="color:#60a5fa;">◆</span>
                <span>{safe_reason}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if len(reasons) > 8:
        with st.expander(f"查看更多判斷依據（{len(reasons) - 8}）"):
            for r in reasons[8:]:
                st.markdown(f"◆ {escape(str(r))}")
