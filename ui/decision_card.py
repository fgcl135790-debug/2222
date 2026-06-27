import streamlit as st
import plotly.graph_objects as go


def render_decision_card(decision):

    action = decision["action"]

    score = decision["score"]

    entry = decision["entry"]

    stop = decision["stop_loss"]

    target = decision["take_profit"]

    rr = decision["rr"]

    reasons = decision["reasons"]

    # ==========================
    # 顏色
    # ==========================

    if action == "BUY":
        color = "#ff1744"
        text = "建議做多"

    elif action == "SELL":
        color = "#00e676"
        text = "建議做空"

    else:
        color = "#ffc107"
        text = "等待"

    # ==========================
    # UI
    # ==========================

    st.subheader("🎯 交易決策")

# ==========================
# Gauge
# ==========================

fig = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=score,
        number={
            "suffix": "%",
            "font": {
                "size": 34
            }
        },
        title={
            "text": "AI Decision"
        },
        gauge={

            "axis": {
                "range": [0,100]
            },

            "bar": {
                "color": color
            },

            "steps":[

                {
                    "range":[0,40],
                    "color":"#3b0d0d"
                },

                {
                    "range":[40,60],
                    "color":"#3f3f3f"
                },

                {
                    "range":[60,100],
                    "color":"#083d17"
                }

            ]
        }
    )
)

fig.update_layout(

    height=230,

    margin=dict(
        l=10,
        r=10,
        t=20,
        b=0
    )

)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.markdown(
    f"## <span style='color:{color}'>{text}</span>",
    unsafe_allow_html=True
)

st.write(f"**進場：** {entry}")

st.write(f"**停損：** {stop}")

st.write(f"**停利：** {target}")

st.write(f"**RR：** {rr}")

st.caption("判斷依據")

for r in reasons:

    st.write("•", r)
