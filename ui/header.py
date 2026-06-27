import streamlit as st

from ui.cards import metric_card


def draw_header(price,
                ai,
                rebound,
                master,
                risk,
                status):

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        metric_card(
            "現價",
            f"{price:.1f}",
            "",
            "#ff5252"
        )

    with c2:
        metric_card(
            "AI信心",
            f"{ai}%",
            "偏多" if ai > 60 else "偏空",
            "#5eead4",
            ai / 100
        )

    with c3:
        metric_card(
            "反彈率",
            f"{rebound}%",
            "",
            "#34d399",
            rebound / 100
        )

    with c4:
        metric_card(
            "主力動向",
            master,
            "",
            "#ef4444"
        )

    with c5:
        metric_card(
            "風險",
            risk,
            "",
            "#f59e0b"
        )

    with c6:
        metric_card(
            "狀態",
            status,
            "",
            "#4ade80"
        )
