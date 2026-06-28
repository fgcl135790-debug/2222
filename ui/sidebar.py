import streamlit as st


def render_sidebar(reset_callback):

    with st.sidebar:

        st.title("⚙️ 控制中心")

        stock_code = st.text_input(
            "股票代號",
            "2330"
        )

        data_source = st.radio(
            "資料來源",
            [
                "真實盤",
                "模擬盤"
            ]
        )

        api_key = st.text_input(
            "Fugle API Key",
            type="password"
            key="fugle_api_key",
        )

        mode = st.selectbox(
            "AI模式",
            [
                "一般",
                "激進",
                "保守"
            ]
        )

        refresh_sec = st.slider(
            "更新秒數",
            1,
            5,
            2
        )

        if st.button("重置股票"):
            reset_callback()
            st.rerun()

    return (
        stock_code,
        data_source,
        api_key,
        mode,
        refresh_sec,
    )
