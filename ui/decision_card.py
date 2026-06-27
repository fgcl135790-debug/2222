import streamlit as st


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

    st.markdown(
        f"""
<div style="
background:#111827;
padding:18px;
border-radius:14px;
border:1px solid rgba(255,255,255,0.08);
">

<h2 style="color:{color};margin:0;">
{text}
</h2>

<hr>

<b>決策分數：</b> {score}<br><br>

<b>進場：</b> {entry}<br>

<b>停損：</b> {stop}<br>

<b>停利：</b> {target}<br>

<b>RR：</b> {rr}

<hr>

<b>判斷依據</b>

<ul>
"""
        + "".join([f"<li>{r}</li>" for r in reasons])
        + """
</ul>

</div>
""",
        unsafe_allow_html=True,
    )
