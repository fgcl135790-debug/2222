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


def render_trade_alert_panel(alert):

    level = alert.get("level", "WAIT")
    title = escape(str(alert.get("title", "等待訊號")))
    message = escape(str(alert.get("message", "-")))
    detail = escape(str(alert.get("detail", "-")))
    score = escape(str(alert.get("score", 0)))

    if level == "SUCCESS":
        color = UP_COLOR
        icon = "✅"

    elif level == "DANGER":
        color = DOWN_COLOR
        icon = "⚠️"

    elif level == "ENTRY":
        color = WAIT_COLOR
        icon = "🎯"

    elif level == "WARNING":
        color = WAIT_COLOR
        icon = "🟡"

    else:
        color = SUBTEXT
        icon = "⏳"

    st.markdown("### 🚨 進出場提醒")

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
            border-left: 4px solid {color};
            border-radius: 14px;
            padding: 11px 12px;
            box-sizing: border-box;
            width: 100%;
        }}

        .top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 7px;
        }}

        .title {{
            font-size: 15px;
            font-weight: 900;
            color: {color};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .score {{
            font-size: 11px;
            color: {SUBTEXT};
            white-space: nowrap;
        }}

        .message {{
            font-size: 12.5px;
            color: {TEXT};
            line-height: 1.35;
            margin-bottom: 7px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .detail {{
            font-size: 11.5px;
            color: {SUBTEXT};
            line-height: 1.3;
            padding-top: 7px;
            border-top: 1px solid rgba(255,255,255,0.08);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
    </style>
</head>

<body>
    <div class="card">

        <div class="top">
            <div class="title">{icon} {title}</div>
            <div class="score">Score {score}</div>
        </div>

        <div class="message">
            {message}
        </div>

        <div class="detail">
            {detail}
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=112,
        scrolling=False,
    )
