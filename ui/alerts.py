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


def _style(level):

    if level == "BUY":
        return UP_COLOR, "🔴"

    if level == "SELL":
        return DOWN_COLOR, "🟢"

    if level == "DANGER":
        return DOWN_COLOR, "⚠️"

    if level == "SUCCESS":
        return UP_COLOR, "✅"

    if level == "ENTRY":
        return WAIT_COLOR, "🎯"

    if level == "WARNING":
        return WAIT_COLOR, "🟡"

    if level == "WAIT":
        return SUBTEXT, "⏳"

    return SUBTEXT, "🔔"


def render_alerts(alerts):

    st.markdown("### 🔔 即時警示")

    if not alerts:
        alerts = [{
            "level": "INFO",
            "title": "目前無重大警示",
            "message": "行情暫時沒有明顯異常。",
        }]

    rows_html = ""

    for alert in alerts:

        level = alert.get("level", "INFO")
        title = alert.get("title", "-")
        message = alert.get("message", "-")

        color, icon = _style(level)

        rows_html += f"""
        <div class="alert-row" style="border-left:4px solid {color};">
            <div class="alert-title" style="color:{color};">
                {icon} {title}
            </div>
            <div class="alert-message">
                {message}
            </div>
        </div>
        """

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
                padding: 10px;
                box-sizing: border-box;
                width: 100%;
            }}

            .alert-row {{
                background: rgba(255,255,255,0.035);
                border-radius: 10px;
                padding: 9px 10px;
                margin-bottom: 8px;
                box-sizing: border-box;
            }}

            .alert-row:last-child {{
                margin-bottom: 0;
            }}

            .alert-title {{
                font-size: 14px;
                font-weight: 900;
                margin-bottom: 4px;
            }}

            .alert-message {{
                color: {SUBTEXT};
                font-size: 12px;
                line-height: 1.45;
            }}
        </style>
    </head>

    <body>
        <div class="card">
            {rows_html}
        </div>
    </body>
    </html>
    """

    height = 70 + len(alerts) * 72

    components.html(
        html,
        height=height,
        scrolling=False,
    )
