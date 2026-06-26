with col3:

    color = "#00e676" if rebound_rate > 60 else "#ff1744" if rebound_rate < 40 else "#ffc107"

    # =========================
    # 🧠 多層級市場判讀（V6核心）
    # =========================
    if rebound_rate >= 75:
        label = "強勢反彈"
        desc = "主力回補明顯，多方動能強"
        signal_hint = "可偏多操作"
        risk_text = "低風險"
    elif rebound_rate >= 60:
        label = "偏多反彈"
        desc = "買盤優於賣盤，短線轉強"
        signal_hint = "可短多"
        risk_text = "中低風險"
    elif rebound_rate >= 45:
        label = "震盪整理"
        desc = "多空平衡，方向未明"
        signal_hint = "觀望為主"
        risk_text = "中性風險"
    elif rebound_rate >= 30:
        label = "偏弱反彈"
        desc = "賣壓略大，反彈有限"
        signal_hint = "避免追多"
        risk_text = "中高風險"
    else:
        label = "弱勢下跌"
        desc = "空方主導，續跌機率高"
        signal_hint = "偏空觀察"
        risk_text = "高風險"

    # =========================
    # 🎨 UI（券商級卡片）
    # =========================
    st.markdown(f"""
    <div style="
        background:#0f172a;
        padding:16px;
        border-radius:14px;
        border:1px solid rgba(255,255,255,0.08);
        height:140px;
    ">

        <div style="color:#9ca3af;font-size:12px;">
            反彈機率
        </div>

        <div style="
            font-size:26px;
            font-weight:800;
            color:{color};
            margin-top:4px;
        ">
            {rebound_rate}%
        </div>

        <div style="
            margin-top:6px;
            font-size:14px;
            font-weight:700;
            color:{color};
        ">
            {label}
        </div>

        <div style="
            margin-top:4px;
            font-size:12px;
            color:#cbd5e1;
        ">
            {desc}
        </div>

        <div style="
            margin-top:6px;
            font-size:12px;
            color:#94a3b8;
        ">
            👉 {signal_hint} ｜ {risk_text}
        </div>

    </div>
    """, unsafe_allow_html=True)

    # =========================
    # 📊 視覺條（加強券商感）
    # =========================
    st.progress(rebound_rate / 100)
