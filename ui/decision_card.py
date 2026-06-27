import streamlit as st
import plotly.graph_objects as go


def render_decision_card(decision):

    action = decision.get("action", "WAIT")
    score = decision.get("score", 50)

    entry = decision.get("entry", "-")
    stop = decision.get("stop_loss", "-")
    target = decision.get("take_profit", "-")
    rr = decision.get("rr", "-")
    reasons = decision.get("reasons", [])

    # ------------------------
    # 顏色
    # ------------------------

    if action == "BUY":
        color = "#ff5252"      # 台股：做多＝紅
        title = "可當沖做多"

    elif action == "SELL":
        color = "#00e676"      # 台股：做空＝綠
        title = "可當沖做空"

    else:
        color = "#ffc107"
        title = "等待進場"

    st.markdown("### 🎯 交易決策 (V7.5)")

    left, right = st.columns([3, 2])

    # ==========================
    # 左邊
    # ==========================

    with left:

        st.markdown(
            f"""
            <div style="
            font-size:30px;
            font-weight:700;
            color:{color};
            ">
            {title}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")

        st.markdown(f"**進場區間**　{entry}")
        st.markdown(f"**停損價位**　{stop}")
        st.markdown(f"**停利目標**　{target}")
        st.markdown(f"**風險報酬比**　{rr}")

    # ==========================
    # 右邊 Gauge
    # ==========================

    with right:

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=score,
                number={
                    "suffix": "",
                    "font": {"size": 34},
                },
                gauge={
                    "shape": "angular",

                    "axis": {
                        "range": [0, 100]
                    },

                    "bar": {
                        "color": color,
                        "thickness": 0.25
                    },

                    "bgcolor": "#1b1f2a",

                    "steps": [

                        {
                            "range": [0, 30],
                            "color": "#401515"
                        },

                        {
                            "range": [30, 60],
                            "color": "#665522"
                        },

                        {
                            "range": [60, 80],
                            "color": "#225533"
                        },

                        {
                            "range": [80, 100],
                            "color": "#00c853"
                        }

                    ]
                }
            )
        )

        fig.update_layout(
            height=220,
            margin=dict(
                l=0,
                r=0,
                t=10,
                b=0
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.divider()

    st.markdown("#### AI 判斷依據")

    if len(reasons) == 0:

        st.write("目前無分析內容")

    else:

        for r in reasons:

            st.markdown(f"✅ {r}")
