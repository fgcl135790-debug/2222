import streamlit as st
import plotly.graph_objects as go

from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
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

    entry = _fmt(decision.get("entry", "-"))
    stop = _fmt(decision.get("stop_loss", "-"))
    target = _fmt(decision.get("take_profit", "-"))
    rr = _fmt(decision.get("rr", "-"))
    reasons = decision.get("reasons", [])

    # =========================
    # 台股顏色
    # =========================

    if action == "BUY":
        color = UP_COLOR
        title = "可當沖做多"

    elif action == "SELL":
        color = DOWN_COLOR
        title = "可當沖做空"

    else:
        color = WAIT_COLOR
        title = "等待進場"

    st.markdown("### 🎯 交易決策 (V7.5)")

    left, right = st.columns([3, 2])

    # =========================
    # 左側資訊
    # =========================

    with left:

        st.markdown(
            f"""
            <div style="
                font-size:28px;
                font-weight:900;
                color:{color};
                margin-bottom:8px;
            ">
                {title}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(f"**進場區間**　{entry}")
        st.markdown(f"**停損價位**　{stop}")
        st.markdown(f"**停利目標**　{target}")
        st.markdown(f"**風險報酬比**　{rr}")

    # =========================
    # 右側 Gauge
    # =========================

    with right:

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=score,
                number={
                    "font": {
                        "size": 32,
                        "color": "#ffffff",
                    }
                },
                gauge={
                    "shape": "angular",
                    "axis": {
                        "range": [0, 100],
                        "tickwidth": 0,
                        "tickcolor": "rgba(255,255,255,0)",
                    },
                    "bar": {
                        "color": color,
                        "thickness": 0.25,
                    },
                    "bgcolor": "#1b1f2a",
                    "borderwidth": 0,
                    "steps": [
                        {
                            "range": [0, 30],
                            "color": "#401515",
                        },
                        {
                            "range": [30, 60],
                            "color": "#665522",
                        },
                        {
                            "range": [60, 80],
                            "color": "#225533",
                        },
                        {
                            "range": [80, 100],
                            "color": "#00c853",
                        },
                    ],
                },
            )
        )

        fig.update_layout(
            height=210,
            margin=dict(
                l=0,
                r=0,
                t=10,
                b=0,
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                color="#ffffff",
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key=f"decision_gauge_{id(fig)}",
        )

    st.divider()

    st.markdown("#### AI 判斷依據")

    if not reasons:

        st.write("目前無分析內容")

    else:

        for r in reasons:

            st.markdown(f"🔹 {r}")
