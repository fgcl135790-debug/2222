import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    CARD_BG,
    CARD_BORDER,
    TEXT,
    SUBTEXT,
)


def render_big_order_panel(big_order_log):

    st.markdown("### 🐋 主力大單")

    if not big_order_log:
        st.caption("目前尚未偵測到主力大單")
        return

    latest = big_order_log[-1]

    direction = latest.get("direction", "UNKNOWN")

    if direction == "BUY":
        color = UP_COLOR
        direction_icon = "🔴"

    elif direction == "SELL":
        color = DOWN_COLOR
        direction_icon = "🟢"

    else:
        color = WAIT_COLOR
        direction_icon = "🟡"

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
                margin-bottom: 10px;
            }}

            .title {{
                font-size: 15px;
                font-weight: 800;
                color: {color};
            }}

            .time {{
                font-size: 12px;
                color: {SUBTEXT};
            }}

            .main {{
                font-size: 24px;
                font-weight: 900;
                color: {color};
                margin-bottom: 6px;
            }}

            .row {{
                display: flex;
                justify-content: space-between;
                font-size: 13px;
                color: {TEXT};
                margin-top: 6px;
            }}

            .label {{
                color: {SUBTEXT};
            }}
        </style>
    </head>

    <body>
        <div class="card">

            <div class="top">
                <div class="title">{direction_icon} {latest.get("direction_text", "-")}</div>
                <div class="time">{latest.get("time", "-")}</div>
            </div>

            <div class="main">
                {latest.get("volume_lot", "-")} 張
            </div>

            <div class="row">
                <div class="label">成交價</div>
                <div>{latest.get("price", "-")}</div>
            </div>

            <div class="row">
                <div class="label">大單門檻</div>
                <div>{latest.get("threshold_lot", "-")} 張</div>
            </div>

            <div class="row">
                <div class="label">強度</div>
                <div>{latest.get("strength", "-")}</div>
            </div>

        </div>
    </body>
    </html>
    """

    components.html(
        html,
        height=155,
        scrolling=False,
    )

    rows = []

    for item in big_order_log[-8:][::-1]:

        rows.append({
            "時間": item.get("time", "-"),
            "方向": item.get("direction_text", "-"),
            "價格": item.get("price", "-"),
            "張數": item.get("volume_lot", "-"),
            "強度": item.get("strength", "-"),
        })

    df = pd.DataFrame(rows)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=245,
    )
