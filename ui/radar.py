import streamlit as st


def render_radar(bids, asks):

    st.subheader("📡 主力雷達")

    bid_ratio = sum([b["size"] for b in bids]) / max(
        sum([a["size"] for a in asks]),
        1
    )

    if bid_ratio > 1.3:

        st.markdown("""
        <div style="
            color:#ff1744;
            font-weight:700;
            font-size:16px;
        ">
            🔴 主力吃貨（偏多）
        </div>
        """, unsafe_allow_html=True)

    elif bid_ratio < 0.8:

        st.markdown("""
        <div style="
            color:#00e676;
            font-weight:700;
            font-size:16px;
        ">
            🟢 主力出貨（偏空）
        </div>
        """, unsafe_allow_html=True)

    else:

        st.markdown("""
        <div style="
            color:#ffc107;
            font-weight:700;
            font-size:16px;
        ">
            🟡 籌碼平衡
        </div>
        """, unsafe_allow_html=True)
