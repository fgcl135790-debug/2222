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


def _fmt_price(value):
    value = _safe_float(value)

    if value <= 0:
        return "-"

    return f"{value:.1f}"


def _fmt_size(value):
    value = _safe_float(value)

    if value <= 0:
        return "-"

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


def render_orderbook(bids, asks):

    st.markdown("### 📋 五檔報價")

    bids = _normalize(bids)
    asks = _normalize(asks)

    bid_total = sum([b["size"] for b in bids])
    ask_total = sum([a["size"] for a in asks])

    ratio = bid_total / max(ask_total, 1)

    bid_color = DOWN_COLOR   # 買盤量用綠
    ask_color = UP_COLOR     # 賣盤量用紅

    if ratio >= 1.3:
        status = "買盤偏強"
        status_color = bid_color

    elif ratio <= 0.77:
        status = "賣壓偏強"
        status_color = ask_color

    else:
        status = "委買委賣均衡"
        status_color = WAIT_COLOR

    rows_html = ""

    for i in range(5):
        b = bids[i]
        a = asks[i]

        rows_html += f"""
        <tr>
            <td class="bid-size">{_fmt_size(b["size"])}</td>
            <td class="bid-price">{_fmt_price(b["price"])}</td>
            <td class="ask-price">{_fmt_price(a["price"])}</td>
            <td class="ask-size">{_fmt_size(a["size"])}</td>
        </tr>
        """

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

        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 14px;
            padding: 12px;
            box-sizing: border-box;
            width: 100%;
        }}

        .top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .title {{
            font-size: 13px;
            font-weight: 900;
            color: {TEXT};
        }}

        .status {{
            font-size: 12px;
            font-weight: 900;
            color: {status_color};
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}

        th {{
            color: {SUBTEXT};
            font-size: 12px;
            font-weight: 800;
            padding: 6px 4px;
            border-bottom: 1px solid rgba(255,255,255,0.12);
        }}

        td {{
            font-size: 13px;
            font-weight: 900;
            text-align: center;
            padding: 6px 4px;
            border-bottom: 1px solid rgba(255,255,255,0.07);
        }}

        .bid-size {{
            color: {bid_color};
        }}

        .bid-price {{
            color: {bid_color};
        }}

        .ask-price {{
            color: {ask_color};
        }}

        .ask-size {{
            color: {ask_color};
        }}

        .summary {{
            margin-top: 10px;
            padding-top: 9px;
            border-top: 1px solid rgba(255,255,255,0.08);
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }}

        .box {{
            background: rgba(255,255,255,0.035);
            border-radius: 10px;
            padding: 8px;
            text-align: center;
        }}

        .label {{
            color: {SUBTEXT};
            font-size: 11px;
            margin-bottom: 4px;
        }}

        .value {{
            font-size: 15px;
            font-weight: 900;
            color: {TEXT};
        }}

        .ratio {{
            color: {status_color};
        }}
    </style>
</head>

<body>
    <div class="card">

        <div class="top">
            <div class="title">即時五檔</div>
            <div class="status">{status}</div>
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
                <div class="label">買量合計</div>
                <div class="value" style="color:{bid_color};">{_fmt_size(bid_total)}</div>
            </div>

            <div class="box">
                <div class="label">買賣比</div>
                <div class="value ratio">{ratio:.2f}</div>
            </div>

            <div class="box">
                <div class="label">賣量合計</div>
                <div class="value" style="color:{ask_color};">{_fmt_size(ask_total)}</div>
            </div>
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=286,
        scrolling=False,
    )
