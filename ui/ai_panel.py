# =========================
# 🧠 AI 判讀（V5.5 修正版）
# =========================

import streamlit as st


def render_ai_panel(
    signal,
    score,
    rebound,
):

    st.subheader("🧠 AI 判讀")

    ai_confidence = score
    rebound_rate = rebound

    col1, col2, col3 = st.columns(3, gap="large")

# ======================
# 🔴 / 🟢 訊號（台股制）
# ======================
    with col1:
        if signal == "BUY":
            st.markdown("""
            <div style="
                background:#3b0d0d;
                padding:14px;
                border-radius:12px;
                display:flex;
                align-items:center;
                gap:10px;
                height:80px;
            ">
                <div style="width:10px;height:10px;border-radius:50%;
                            background:#ff1744;box-shadow:0 0 8px #ff1744;"></div>
                <div style="color:#ff5252;font-weight:700;">
                    做多訊號
                </div>
            </div>
            """, unsafe_allow_html=True)

        elif signal == "SELL":
            st.markdown("""
            <div style="
                background:#0b3d1f;
                padding:14px;
                border-radius:12px;
                display:flex;
                align-items:center;
                gap:10px;
                height:80px;
            ">
                <div style="width:10px;height:10px;border-radius:50%;
                            background:#00e676;box-shadow:0 0 8px #00e676;"></div>
                <div style="color:#00e676;font-weight:700;">
                    做空訊號
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.info("盤整")

# ======================
# 🧠 AI信心（中）
# ======================
    with col2:
        st.markdown("""
        <div style="
            background:#111827;
            padding:14px;
            border-radius:12px;
            height:80px;
        ">
            <div style="color:#9ca3af;font-size:12px;">AI信心</div>
            <div style="font-size:22px;font-weight:700;">
        """ + f"{ai_confidence}%" + """
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.progress(ai_confidence / 100)

# ======================
# 📈 反彈機率（右）V6修正版
# ======================
    with col3:

    # =========================
    # 🧠 判斷邏輯
    # =========================
        if rebound_rate >= 75:
            label = "強勢反彈"
            desc = "主力回補明顯，多方動能強"
            signal_hint = "可偏多操作"
            risk_text = "低風險"
            color = "#00e676"

        elif rebound_rate >= 60:
            label = "偏多反彈"
            desc = "買盤優於賣盤，短線轉強"
            signal_hint = "可短多"
            risk_text = "中低風險"
            color = "#22c55e"

        elif rebound_rate >= 45:
            label = "震盪整理"
            desc = "多空平衡，方向未明"
            signal_hint = "觀望為主"
            risk_text = "中性風險"
            color = "#ffc107"

        elif rebound_rate >= 30:
            label = "偏弱反彈"
            desc = "賣壓略大，反彈有限"
            signal_hint = "避免追多"
            risk_text = "中高風險"
            color = "#ff9800"

        else:
            label = "弱勢下跌"
            desc = "空方主導，續跌機率高"
            signal_hint = "偏空觀察"
            risk_text = "高風險"
            color = "#ff1744"

    # =========================
    # 🚀 用 Streamlit 原生 UI（關鍵修正）
    # =========================

        st.markdown("### 📈 反彈機率")

        st.markdown(f"## **{rebound_rate}%**")

        st.markdown(
            f"**<span style='color:{color}'>{label}</span>**",
            unsafe_allow_html=True
        )

        st.write(desc)

        st.caption(f"👉 {signal_hint} ｜ {risk_text}")

    # =========================
    # 📊 進度條（穩定版）
    # =========================
        st.progress(min(max(rebound_rate / 100, 0), 1.0))
