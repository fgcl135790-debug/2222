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
    # 多週期共振資料
    # =========================

    multi_period = decision.get("multi_period", {}) or {}

    multi_status = (
        decision.get("multi_period_status")
        or multi_period.get("status")
        or "尚未判斷"
    )

    resonance = multi_period.get("resonance", "WAIT")
    multi_confidence = _safe_int(multi_period.get("confidence", 0), 0)
    bull_count = _safe_int(multi_period.get("bull_count", 0), 0)
    bear_count = _safe_int(multi_period.get("bear_count", 0), 0)
    wait_count = _safe_int(multi_period.get("wait_count", 0), 0)

    if resonance in ["BULL_STRONG", "BULL"]:
        multi_color = UP_COLOR
        multi_desc = "多週期結構偏多，做多訊號可信度提高。"

    elif resonance in ["BEAR_STRONG", "BEAR"]:
        multi_color = DOWN_COLOR
        multi_desc = "多週期結構偏空，做空訊號可信度提高。"

    elif resonance == "DIVERGENCE":
        multi_color = WAIT_COLOR
        multi_desc = "多週期方向不一致，容易震盪或假突破。"

    else:
        multi_color = WAIT_COLOR
        multi_desc = "三週期尚未形成明確共振，等待方向確認。"

    # =========================
    # 台股顏色
    # =========================

    if action == "BUY":
        color = UP_COLOR
        title = "可當沖做多"
        badge = "BUY"
        desc = "多方策略成立，等待理想進場區。"

    elif action == "SELL":
        color = DOWN_COLOR
        title = "可當沖做空"
        badge = "SELL"
        desc = "空方條件成立，避免追空等待反彈。"

    else:
        color = WAIT_COLOR
        title = "等待進場"
        badge = "WAIT"
        desc = "多空條件尚未同步，暫時觀望。"

    title = escape(title)
    badge = escape(badge)
    desc = escape(desc)
    multi_status = escape(str(multi_status))
    multi_desc = escape(str(multi_desc))

    degree = int(score * 3.6)

    # =========================
    # 只顯示前三條重點
    # =========================

    top_reasons = reasons[:3]
    more_reasons = reasons[3:]

    reason_items = ""

    if top_reasons:

        for r in top_reasons:
            reason_items += f"""
            <div class="reason-row">
                <span class="reason-dot">◆</span>
                <span>{escape(str(r))}</span>
            </div>
            """

    else:

        reason_items = """
        <div class="reason-row">
            <span class="reason-dot">◆</span>
            <span>目前無明確判斷依據</span>
        </div>
        """

    more_hint = ""

    if more_reasons:

        more_hint = f"""
        <div class="more-hint">
            另有 {len(more_reasons)} 條判斷依據已收合
        </div>
        """

    st.markdown("### 🎯 交易決策")

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
            background: linear-gradient(135deg, rgba(17,24,39,0.98), rgba(9,14,24,0.98));
            border: 1px solid {CARD_BORDER};
            border-radius: 15px;
            padding: 13px;
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

        .title {{
            color: {color};
            font-size: 27px;
            font-weight: 900;
            line-height: 1.05;
        }}

        .badge {{
            color: {color};
            border: 1px solid {color};
            background: rgba(255,255,255,0.035);
            padding: 4px 9px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 900;
            white-space: nowrap;
        }}

        .main {{
            display: grid;
            grid-template-columns: 1fr 88px;
            gap: 12px;
            align-items: center;
        }}

        .rows {{
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 9px;
        }}

        .row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
            font-size: 12.5px;
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
            width: 82px;
            height: 82px;
            border-radius: 50%;
            background:
                conic-gradient(
                    {color} 0deg,
                    {color} {degree}deg,
                    rgba(255,255,255,0.10) {degree}deg,
                    rgba(255,255,255,0.10) 360deg
                );
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .score-inner {{
            width: 61px;
            height: 61px;
            border-radius: 50%;
            background: #0b111c;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(255,255,255,0.06);
        }}

        .score {{
            font-size: 23px;
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
            margin-top: 9px;
            padding: 8px 9px;
            border-radius: 10px;
            background: rgba(255,255,255,0.035);
            border-left: 4px solid {color};
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.4;
        }}

        .multi {{
            margin-top: 9px;
            padding: 9px;
            border-radius: 11px;
            background: rgba(255,255,255,0.035);
            border-left: 4px solid {multi_color};
        }}

        .multi-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}

        .multi-title {{
            color: {multi_color};
            font-size: 14px;
            font-weight: 900;
        }}

        .multi-score {{
            color: {multi_color};
            border: 1px solid {multi_color};
            border-radius: 999px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 900;
            white-space: nowrap;
        }}

        .multi-desc {{
            color: {SUBTEXT};
            font-size: 11.2px;
            line-height: 1.35;
            margin-bottom: 7px;
        }}

        .multi-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
        }}

        .mini-box {{
            background: rgba(255,255,255,0.035);
            border-radius: 8px;
            padding: 6px 4px;
            text-align: center;
        }}

        .mini-label {{
            color: {SUBTEXT};
            font-size: 10px;
            margin-bottom: 2px;
        }}

        .mini-value {{
            font-size: 13px;
            font-weight: 900;
            color: {TEXT};
        }}

        .reason-card {{
            margin-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 9px;
        }}

        .reason-title {{
            color: {TEXT};
            font-size: 12.5px;
            font-weight: 900;
            margin-bottom: 6px;
        }}

        .reason-row {{
            display: flex;
            gap: 7px;
            align-items: flex-start;
            color: {TEXT};
            font-size: 11.8px;
            line-height: 1.35;
            margin-bottom: 4px;
        }}

        .reason-dot {{
            color: #60a5fa;
            font-size: 10px;
            margin-top: 2px;
        }}

        .more-hint {{
            margin-top: 6px;
            color: {SUBTEXT};
            font-size: 11px;
            text-align: right;
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

            <div class="score-ring">
                <div class="score-inner">
                    <div class="score">{score}</div>
                    <div class="score-unit">/100</div>
                </div>
            </div>

        </div>

        <div class="desc">
            {desc}
        </div>

        <div class="multi">
            <div class="multi-top">
                <div class="multi-title">🔀 {multi_status}</div>
                <div class="multi-score">共振 {multi_confidence}</div>
            </div>

            <div class="multi-desc">{multi_desc}</div>

            <div class="multi-grid">
                <div class="mini-box">
                    <div class="mini-label">多頭週期</div>
                    <div class="mini-value" style="color:{UP_COLOR};">{bull_count}</div>
                </div>

                <div class="mini-box">
                    <div class="mini-label">空頭週期</div>
                    <div class="mini-value" style="color:{DOWN_COLOR};">{bear_count}</div>
                </div>

                <div class="mini-box">
                    <div class="mini-label">觀望週期</div>
                    <div class="mini-value" style="color:{WAIT_COLOR};">{wait_count}</div>
                </div>
            </div>
        </div>

        <div class="reason-card">
            <div class="reason-title">重點依據</div>
            {reason_items}
            {more_hint}
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=380,
        scrolling=False,
    )
