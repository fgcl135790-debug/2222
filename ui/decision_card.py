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

    if action == "BUY":
        color = UP_COLOR
        title = "可當沖做多"
        badge = "BUY"
        desc = "偏多觀察"

    elif action == "SELL":
        color = DOWN_COLOR
        title = "可當沖做空"
        badge = "SELL"
        desc = "偏空觀察"

    else:
        color = WAIT_COLOR
        title = "等待進場"
        badge = "WAIT"
        desc = "等待確認"

    title = escape(title)
    badge = escape(badge)
    desc = escape(desc)

    degree = int(score * 3.6)

    reason_items = ""

    if reasons:
        for r in reasons[:8]:
            safe_reason = escape(str(r))
            reason_items += f"""
            <div class="reason-row">
                <span class="dot">◆</span>
                <span>{safe_reason}</span>
            </div>
            """
    else:
        reason_items = """
        <div class="reason-row">
            <span class="dot">◆</span>
            <span>目前無分析內容</span>
        </div>
        """

    more_text = ""

    if len(reasons) > 8:
        more_text = f"""
        <div class="more-text">
            另有 {len(reasons) - 8} 條判斷依據，之後可放入展開區。
        </div>
        """

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
            overflow: hidden;
        }}

        .wrap {{
            display: flex;
            flex-direction: column;
            gap: 10px;
            width: 100%;
            box-sizing: border-box;
        }}

        .card {{
            background: linear-gradient(135deg, rgba(17,24,39,0.98), rgba(9,14,24,0.98));
            border: 1px solid {CARD_BORDER};
            border-radius: 16px;
            padding: 14px;
            box-sizing: border-box;
            width: 100%;
        }}

        .top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }}

        .small {{
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
            border-radius: 999px;
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 900;
            background: rgba(255,255,255,0.035);
        }}

        .main {{
            display: grid;
            grid-template-columns: 1fr 92px;
            gap: 12px;
            align-items: center;
        }}

        .rows {{
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 10px;
        }}

        .row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 7px;
            font-size: 13px;
        }}

        .k {{
            color: {SUBTEXT};
            font-weight: 700;
        }}

        .v {{
            color: {TEXT};
            font-weight: 900;
            text-align: right;
        }}

        .rr {{
            color: {color};
        }}

        .score-ring {{
            width: 86px;
            height: 86px;
            border-radius: 50%;
            background:
                conic-gradient({color} 0deg, {color} {degree}deg, rgba(255,255,255,0.10) {degree}deg, rgba(255,255,255,0.10) 360deg);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            margin-left: auto;
        }}

        .score-inner {{
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: #0b111c;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(255,255,255,0.06);
        }}

        .score {{
            font-size: 24px;
            font-weight: 900;
            color: #ffffff;
            line-height: 1;
        }}

        .score-unit {{
            font-size: 10px;
            color: {SUBTEXT};
            margin-top: 2px;
        }}

        .desc {{
            text-align: center;
            color: {SUBTEXT};
            font-size: 11px;
            margin-top: 6px;
        }}

        .reason-card {{
            background: rgba(17,24,39,0.88);
            border: 1px solid {CARD_BORDER};
            border-radius: 14px;
            padding: 12px;
            box-sizing: border-box;
            width: 100%;
        }}

        .reason-title {{
            font-size: 13px;
            font-weight: 900;
            margin-bottom: 8px;
            color: {TEXT};
        }}

        .reason-list {{
            max-height: 105px;
            overflow: hidden;
        }}

        .reason-row {{
            display: flex;
            gap: 7px;
            align-items: flex-start;
            color: {TEXT};
            font-size: 12px;
            line-height: 1.45;
            margin-bottom: 5px;
        }}

        .dot {{
            color: #60a5fa;
            font-size: 10px;
            margin-top: 2px;
        }}

        .more-text {{
            margin-top: 8px;
            color: {SUBTEXT};
            font-size: 11px;
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 7px;
        }}
    </style>
</head>

<body>
    <div class="wrap">

        <div class="card">

            <div class="top">
                <div>
                    <div class="small">建議策略</div>
                    <div class="title">{title}</div>
                </div>

                <div class="badge">{badge}</div>
            </div>

            <div class="main">

                <div class="rows">
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

                <div>
                    <div class="score-ring">
                        <div class="score-inner">
                            <div class="score">{score}</div>
                            <div class="score-unit">/100</div>
                        </div>
                    </div>
                    <div class="desc">{desc}</div>
                </div>

            </div>

        </div>

        <div class="reason-card">
            <div class="reason-title">AI 判斷依據</div>
            <div class="reason-list">
                {reason_items}
            </div>
            {more_text}
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=350,
        scrolling=False,
    )
