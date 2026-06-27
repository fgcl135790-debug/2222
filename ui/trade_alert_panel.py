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


def render_trade_alert_panel(alert):

    level = alert.get("level", "WAIT")
    title = alert.get("title", "等待訊號")
    message = alert.get("message", "-")
    detail = alert.get("detail", "-")
    score = alert.get("score", 0)

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
            }}

            .card {{
                background: {CARD_BG};
                border: 1px solid {CARD_BORDER};
                border-radius: 14px;
                padding: 14px;
                box-sizing: border-box;
                width: 100%;
            }}

            .top {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }}

            .title {{
                font-size: 17px;
                font-weight: 900;
                color: {color};
            }}

            .score {{
                font-size: 12px;
                color: {SUBTEXT};
            }}

            .message {{
                font-size: 13px;
                color: {TEXT};
                margin-top: 8px;
                line-height: 1.5;
            }}

            .detail {{
                font-size: 12px;
                color: {SUBTEXT};
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px solid rgba(255,255,255,0.08);
                line-height: 1.5;
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
        height=145,
        scrolling=False,
    )
