import streamlit as st


def render_header(
    name,
    stock_code,
    price,
    score,
    risk,
    state,
):

    st.title(f"🏦 {name} ({stock_code})")

    col1, col2, col3, col4 = st.columns(4)

    cards = [
        ("現價", f"{price:.2f}", "#ffffff"),
        ("AI信心", f"{score}%", "#29b6f6"),
        ("風險", f"{risk}%", "#ffca28"),
        ("狀態", state, "#42a5f5"),
    ]

    for col, (title, value, color) in zip(
        [col1, col2, col3, col4],
        cards,
    ):

        with col:

            st.markdown(
                f"""
<div style="
background:#111827;
border-radius:14px;
padding:16px;
border:1px solid rgba(255,255,255,.08);
height:95px;
">

<div style="
font-size:12px;
color:#9ca3af;
">
{title}
</div>

<div style="
margin-top:10px;
font-size:24px;
font-weight:700;
color:{color};
">
{value}
</div>

</div>
""",
                unsafe_allow_html=True,
            )
