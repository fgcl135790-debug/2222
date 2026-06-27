import streamlit as st


def metric_card(title, value,
                subtitle="",
                color="#ffffff",
                progress=None,
                height=130):

    st.markdown(f"""
    <style>
    .metric-card {{
        background:#111827;
        border-radius:16px;
        padding:18px;
        border:1px solid rgba(255,255,255,.06);
        height:{height}px;
    }}

    .metric-title {{
        color:#94a3b8;
        font-size:13px;
    }}

    .metric-value {{
        color:{color};
        font-size:42px;
        font-weight:800;
        margin-top:6px;
    }}

    .metric-sub {{
        color:#cbd5e1;
        font-size:14px;
        margin-top:4px;
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metric-card">

        <div class="metric-title">
            {title}
        </div>

        <div class="metric-value">
            {value}
        </div>

        <div class="metric-sub">
            {subtitle}
        </div>

    </div>
    """, unsafe_allow_html=True)

    if progress is not None:
        st.progress(progress)
