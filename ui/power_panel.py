import streamlit as st
from textwrap import dedent

from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    CARD_BG,
    CARD_BORDER,
    TEXT,
    SUBTEXT,
)


def _to_int(value, default=0):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def render_power_panel(decision):

    long_score = _to_int(decision.get("long_score", 0))
    short_score = _to_int(decision.get("short_score", 0))
    bias = _to_int(decision.get("bias", long_score - short_score))

    total = max(long_score + short_score, 1)

    long_pct = int(long_score / total * 100)
    short_pct = int(short_score / total * 100)

    if bias >= 4:
        status = "多方優勢"
        status_color = UP_COLOR

    elif bias <= -4:
        status = "空方優勢"
        status_color = DOWN_COLOR

    else:
        status = "多空拉鋸"
        status_color = WAIT_COLOR

    st.markdown("### ⚔️ 多空力道")

    html = f"""
<div style="
    background:{CARD_BG};
    border:1px solid {CARD_BORDER};
    border-radius:14px;
    padding:14px;
    margin-bottom:8px;
">

    <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:10px;
    ">
        <div style="
            font-size:14px;
            color:{SUBTEXT};
        ">
            目前狀態
        </div>

        <div style="
            font-size:18px;
            font-weight:800;
            color:{status_color};
        ">
            {status}
        </div>
    </div>

    <div style="
        display:flex;
        justify-content:space-between;
        margin-bottom:6px;
        font-size:13px;
    ">
        <div style="
            color:{UP_COLOR};
            font-weight:700;
        ">
            多方 {long_score}
        </div>

        <div style="
            color:{DOWN_COLOR};
            font-weight:700;
        ">
            空方 {short_score}
        </div>
    </div>

    <div style="
        width:100%;
        height:10px;
        background:#263241;
        border-radius:99px;
        overflow:hidden;
        margin-bottom:8px;
    ">
        <div style="
            width:{long_pct}%;
            height:100%;
            background:{UP_COLOR};
            float:left;
        "></div>

        <div style="
            width:{short_pct}%;
            height:100%;
            background:{DOWN_COLOR};
            float:left;
        "></div>
    </div>

    <div style="
        display:flex;
        justify-content:space-between;
        color:{SUBTEXT};
        font-size:12px;
    ">
        <div>多方占比 {long_pct}%</div>
        <div>空方占比 {short_pct}%</div>
    </div>

    <div style="
        margin-top:10px;
        padding-top:10px;
        border-top:1px solid rgba(255,255,255,0.08);
        color:{TEXT};
        font-size:13px;
    ">
        多空差距：<b>{bias}</b>
    </div>

</div>
"""

    st.markdown(
        dedent(html),
        unsafe_allow_html=True,
    )
