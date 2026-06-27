import streamlit as st
import streamlit.components.v1 as components

from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    CARD_BG,
    CARD_BORDER,
    TEXT,
    SUBTEXT,
)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _fmt_price(value):
    value = _safe_float(value)

    if value <= 0:
        return "-"

    return f"{value:.1f}"


def _fmt_size(value):
    value = _safe_float(value)

    if value <= 0:
        return "-"

    if value >= 1000:
        return f"{value / 1000:.1f}K"

    if abs(value - round(value)) < 0.01:
        return str(int(round(value)))

    return f"{value:.1f}"


def _normalize(levels):
    rows = []

    for i in range(5):
        if levels and i < len(levels):
            item = levels[i]
        else:
            item = {}

        rows.append({
            "price": _safe_float(item.get("price", 0)),
            "size": _safe_float(item.get("size", 0)),
        })

    return rows


def render_depth_panel(bids, asks, decision):

    bids = _normalize(bids)
    asks = _normalize(asks)

    bid_total = sum([b["size"] for b in bids])
    ask_total = sum([a["size"] for a in asks])

    depth_ratio = bid_total / max(ask_total, 1)

    buy_color = DOWN_COLOR
    sell_color = UP_COLOR

    if depth_ratio >= 1.3:
        depth_status = "委買偏強"
        depth_color = buy_color

    elif depth_ratio <= 0.77:
        depth_status = "委賣偏強"
        depth_color = sell_color

    else:
        depth_status = "委買委賣均衡"
        depth_color = WAIT_COLOR

    long_score = _safe_int(decision.get("long_score", 0))
    short_score = _safe_int(decision.get("short_score", 0))
    bias = _safe_int(decision.get("bias", long_score - short_score))

    force_total = max(long_score + short_score, 1)

    long_pct = int(long_score / force_total * 100)
    short_pct = int(short_score / force_total * 100)

    if bias >= 4:
        force_status = "多方優勢"
        force_color = UP_COLOR
        strategy = "偏多觀察"

    elif bias <= -4:
        force_status = "空方優勢"
        force_color = DOWN_COLOR
        strategy = "避免追多"

    else:
        force_status = "多空拉鋸"
        force_color = WAIT_COLOR
        strategy = "等待確認"

    rows_html = ""

    for i in range(5):
        b = bids[i]
        a = asks[i]

        rows_html += f"""
        <tr>
            <td class="buy-size">{_fmt_size(b["size"])}</td>
            <td class="buy-price">{_fmt_price(b["price"])}</td>
            <td class="sell-price">{_fmt_price(a["price"])}</td>
            <td class="sell-size">{_fmt_size(a["size"])}</td>
        </tr>
        """

    st.markdown("### 📊 委買委賣 / 多空力道")

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

        .wrap {{
            display: grid;
            grid-template-columns: 1.08fr 0.92fr;
            gap: 10px;
            width: 100%;
            box-sizing: border-box;
        }}

        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 14px;
            padding: 11px;
            box-sizing: border-box;
            width: 100%;
            height: 100%;
        }}

        .top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 7px;
        }}

        .title {{
            color: {TEXT};
            font-size: 13px;
            font-weight: 900;
        }}

        .status {{
            font-size: 13px;
            font-weight: 900;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}

        th {{
            color: {SUBTEXT};
            font-size: 11.5px;
            font-weight: 800;
            padding: 5px 3px;
            border-bottom: 1px solid rgba(255,255,255,0.12);
        }}

        td {{
            font-size: 12.5px;
            font-weight: 900;
            text-align: center;
            padding: 5px 3px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}

        .buy-size,
        .buy-price {{
            color: {buy_color};
        }}

        .sell-price,
        .sell-size {{
            color: {sell_color};
        }}

        .summary {{
            margin-top: 8px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
        }}

        .box {{
            background: rgba(255,255,255,0.035);
            border-radius: 9px;
            padding: 7px 5px;
            text-align: center;
        }}

        .box-label {{
            color: {SUBTEXT};
            font-size: 10.5px;
            margin-bottom: 3px;
        }}

        .box-value {{
            font-size: 14px;
            font-weight: 900;
        }}

        .force-head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .force-status {{
            color: {force_color};
            font-size: 20px;
            font-weight: 900;
        }}

        .force-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}

        .long {{
            color: {UP_COLOR};
            font-size: 13px;
            font-weight: 900;
        }}

        .short {{
            color: {DOWN_COLOR};
            font-size: 13px;
            font-weight: 900;
        }}

        .bar {{
            width: 100%;
            height: 13px;
            background: rgba(255,255,255,0.10);
            border-radius: 999px;
            overflow: hidden;
            display: flex;
            margin-bottom: 7px;
        }}

        .long-bar {{
            width: {long_pct}%;
            height: 100%;
            background: {UP_COLOR};
        }}

        .short-bar {{
            width: {short_pct}%;
            height: 100%;
            background: {DOWN_COLOR};
        }}

        .pct-row {{
            display: flex;
            justify-content: space-between;
            color: {SUBTEXT};
            font-size: 11.5px;
            margin-bottom: 8px;
        }}

        .mini-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
        }}

        .hint {{
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(255,255,255,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }}

        .hint-left {{
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.35;
        }}

        .hint-right {{
            color: {force_color};
            font-size: 15px;
            font-weight: 900;
            white-space: nowrap;
        }}

        @media (max-width: 900px) {{
            .wrap {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>

<body>
    <div class="wrap">

        <div class="card">

            <div class="top">
                <div class="title">即時五檔</div>
                <div class="status" style="color:{depth_color};">{depth_status}</div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>買量</th>
                        <th>買價</th>
                        <th>賣價</th>
                        <th>賣量</th>
                    </tr>
                </thead>

                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <div class="summary">
                <div class="box">
                    <div class="box-label">委買</div>
                    <div class="box-value" style="color:{buy_color};">{_fmt_size(bid_total)}</div>
                </div>

                <div class="box">
                    <div class="box-label">買賣比</div>
                    <div class="box-value" style="color:{depth_color};">{depth_ratio:.2f}</div>
                </div>

                <div class="box">
                    <div class="box-label">委賣</div>
                    <div class="box-value" style="color:{sell_color};">{_fmt_size(ask_total)}</div>
                </div>
            </div>

        </div>

        <div class="card">

            <div class="force-head">
                <div>
                    <div class="title">多空力道</div>
                    <div style="color:{SUBTEXT};font-size:11.5px;margin-top:3px;">DecisionEngine 綜合判斷</div>
                </div>

                <div class="force-status">{force_status}</div>
            </div>

            <div class="force-row">
                <div class="long">多方 {long_score}</div>
                <div class="short">空方 {short_score}</div>
            </div>

            <div class="bar">
                <div class="long-bar"></div>
                <div class="short-bar"></div>
            </div>

            <div class="pct-row">
                <div>多方 {long_pct}%</div>
                <div>空方 {short_pct}%</div>
            </div>

            <div class="mini-grid">

                <div class="box">
                    <div class="box-label">多空差距</div>
                    <div class="box-value" style="color:{force_color};">{bias}</div>
                </div>

                <div class="box">
                    <div class="box-label">目前策略</div>
                    <div class="box-value" style="color:{WAIT_COLOR};">{strategy}</div>
                </div>

                <div class="box">
                    <div class="box-label">委買比</div>
                    <div class="box-value" style="color:{depth_color};">{depth_ratio:.2f}</div>
                </div>

                <div class="box">
                    <div class="box-label">狀態</div>
                    <div class="box-value" style="color:{force_color};">{force_status}</div>
                </div>

            </div>

            <div class="hint">
                <div class="hint-left">
                    五檔與多空分數綜合參考。
                </div>

                <div class="hint-right">
                    {strategy}
                </div>
            </div>

        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=275,
        scrolling=False,
    )
