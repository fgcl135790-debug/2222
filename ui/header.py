import streamlit as st
import streamlit.components.v1 as components
from html import escape

from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    CARD_BG,
    CARD_BORDER,
    TEXT,
    SUBTEXT,
)


def _safe_int(value, default=0):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _risk_style(risk):
    text = str(risk)

    if "高" in text:
        return DOWN_COLOR, "高風險", "請降低追價"

    if "中" in text:
        return WAIT_COLOR, "中低風險", "風險可控"

    if "%" in text:
        value = _safe_int(text.replace("%", ""), 0)

        if value >= 60:
            return DOWN_COLOR, f"{value}%", "風險偏高"

        if value >= 30:
            return WAIT_COLOR, f"{value}%", "風險中等"

        return UP_COLOR, f"{value}%", "風險偏低"

    return WAIT_COLOR, text, "風險監控中"


def _force_style(bid_ratio):
    bid_ratio = _safe_float(bid_ratio, 1.0)

    if bid_ratio >= 1.5:
        return UP_COLOR, "主力吸籌", "籌碼集中偏多"

    if bid_ratio >= 1.15:
        return UP_COLOR, "買盤偏強", "買方略強"

    if bid_ratio <= 0.6:
        return DOWN_COLOR, "主力出貨", "賣壓明顯偏空"

    if bid_ratio <= 0.85:
        return DOWN_COLOR, "賣盤偏強", "賣方略強"

    return WAIT_COLOR, "主力觀望", "多空拉鋸"


def _status_style(signal, state):
    state_text = str(state)

    if signal == "BUY":
        return UP_COLOR, "多頭強勢", "趨勢向上"

    if signal == "SELL":
        return DOWN_COLOR, "空頭偏強", "趨勢向下"

    if "多" in state_text:
        return UP_COLOR, state_text, "趨勢偏多"

    if "空" in state_text:
        return DOWN_COLOR, state_text, "趨勢偏空"

    return WAIT_COLOR, state_text, "等待突破"


def render_header(
    name,
    stock_code,
    price,
    score,
    rebound,
    risk,
    state,
    signal,
    bid_ratio,
    now,
    connection_status="連線正常",
    data_source="真實盤",
):
    name = escape(str(name))
    stock_code = escape(str(stock_code))

    price = _safe_float(price)
    score = max(0, min(100, _safe_int(score)))
    rebound = max(0, min(100, _safe_int(rebound)))

    time_text = now.strftime("%H:%M:%S") if hasattr(now, "strftime") else str(now)

    conn_color = UP_COLOR if "正常" in str(connection_status) else DOWN_COLOR
    source_text = "即時更新" if data_source == "真實盤" else "模擬盤"

    rebound_color = UP_COLOR if rebound >= 60 else WAIT_COLOR if rebound >= 40 else DOWN_COLOR

    risk_color, risk_title, risk_sub = _risk_style(risk)
    force_color, force_title, force_sub = _force_style(bid_ratio)
    status_color, status_title, status_sub = _status_style(signal, state)

    # =========================
    # 原生 Topbar
    # =========================

    topbar_html = (
        f'<div style="width:100%;display:flex;justify-content:space-between;align-items:center;'
        f'margin:0 0 10px 0;padding:2px 4px;box-sizing:border-box;">'
        f'<div style="display:flex;align-items:center;gap:8px;font-size:17px;font-weight:900;'
        f'color:{TEXT};white-space:nowrap;">'
        f'🏦 {name} ({stock_code}) <span style="color:#facc15;">★</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:14px;color:{SUBTEXT};font-size:12px;'
        f'white-space:nowrap;">'
        f'<span>◎ {source_text} {time_text}</span>'
        f'<span><span style="display:inline-block;width:8px;height:8px;border-radius:99px;'
        f'background:{conn_color};box-shadow:0 0 8px {conn_color};margin-right:5px;"></span>'
        f'{connection_status}</span>'
        f'<span>⚙ 設定</span>'
        f'<span>🔔 聲音警示</span>'
        f'<span>自訂布局</span>'
        f'</div>'
        f'</div>'
    )

    st.markdown(
        topbar_html,
        unsafe_allow_html=True,
    )

    # =========================
    # 狀態卡片
    # =========================

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: Arial, "Microsoft JhengHei", sans-serif;
            color: {TEXT};
            overflow: hidden;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 10px;
            width: 100%;
        }}

        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 12px;
            padding: 11px 13px;
            min-height: 78px;
            box-sizing: border-box;
        }}

        .label {{
            color: {SUBTEXT};
            font-size: 12px;
            margin-bottom: 6px;
        }}

        .value {{
            font-size: 25px;
            line-height: 1.05;
            font-weight: 900;
            margin-bottom: 6px;
        }}

        .midvalue {{
            font-size: 20px;
            line-height: 1.1;
            font-weight: 900;
            margin-bottom: 6px;
        }}

        .sub {{
            color: {SUBTEXT};
            font-size: 11px;
            font-weight: 600;
        }}

        .bar {{
            width: 100%;
            height: 7px;
            background: rgba(255,255,255,0.12);
            border-radius: 999px;
            overflow: hidden;
            margin-top: 8px;
        }}

        .bar-fill {{
            height: 100%;
            border-radius: 999px;
        }}

        @media (max-width: 900px) {{
            .grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>

<body>

    <div class="grid">

        <div class="card">
            <div class="label">現價</div>
            <div class="value" style="color:{UP_COLOR};">{price:.2f}</div>
            <div class="sub">即時價</div>
        </div>

        <div class="card">
            <div class="label">AI信心</div>
            <div class="value" style="color:#38bdf8;">{score}%</div>
            <div class="bar">
                <div class="bar-fill" style="width:{score}%; background:#22c55e;"></div>
            </div>
        </div>

        <div class="card">
            <div class="label">反彈機率</div>
            <div class="value" style="color:{rebound_color};">{rebound}%</div>
            <div class="sub">偏多反彈</div>
        </div>

        <div class="card">
            <div class="label">主力動向</div>
            <div class="midvalue" style="color:{force_color};">{force_title}</div>
            <div class="sub">{force_sub}</div>
        </div>

        <div class="card">
            <div class="label">風險等級</div>
            <div class="midvalue" style="color:{risk_color};">{risk_title}</div>
            <div class="sub">{risk_sub}</div>
        </div>

        <div class="card">
            <div class="label">狀態</div>
            <div class="midvalue" style="color:{status_color};">{status_title}</div>
            <div class="sub">{status_sub}</div>
        </div>

    </div>

</body>
</html>
"""

    components.html(
        html,
        height=92,
        scrolling=False,
    )
