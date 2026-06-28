import streamlit as st


def render_sidebar(reset_callback):

    with st.sidebar:

        st.title("⚙️ 控制中心")

        stock_code = st.text_input(
            "股票代號",
            value="2330",
            key="sidebar_stock_code",
        )

        data_source = st.radio(
            "資料來源",
            [
                "真實盤",
                "模擬盤",
            ],
            key="sidebar_data_source",
        )

        api_key = st.text_input(
            "Fugle API Key",
            type="password",
            key="fugle_api_key",
        )

        api_key = (api_key or "").strip()

        # 強制同步給 app.py 主程式使用
        st.session_state["runtime_fugle_api_key"] = api_key

        st.caption("API KEY：已讀取" if api_key else "API KEY：未讀取")

        mode = st.selectbox(
            "AI模式",
            [
                "一般",
                "激進",
                "保守",
            ],
            key="sidebar_ai_mode",
        )

        refresh_sec = st.slider(
            "更新秒數",
            1,
            5,
            2,
            key="sidebar_refresh_sec",
        )

        if st.button("重置股票", key="sidebar_reset_stock"):
            reset_callback()
            st.rerun()

    return (
        stock_code,
        data_source,
        api_key,
        mode,
        refresh_sec,
    )
