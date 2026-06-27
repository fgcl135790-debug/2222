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


def _fmt_value(value):
    if value is None:
        return "-"

    try:
        value = float(value)
        return f"{value:.2f}"
    except Exception:
        return str(value)


def _normalize(levels):
    rows = []

    for i in range(5):
        if levels and i < len(levels):
            item = levels[i]
        else:
            item = {}

        rows.append(
            {
                "price": _safe_float(item.get("price", 0)),
                "size": _safe_float(item.get("size", 0)),
            }
        )

    return rows


def render_depth_panel(bids, asks, decision):

    bids = _normalize(bids)
    asks = _normalize(asks)

    bid_total = sum([b["size"] for b in bids])
    ask_total = sum([a["size"] for a in asks])

    depth_ratio = bid_total / max(ask_total, 1)

    # 五檔顏色：買方多為低於現價，偏綠；賣方多為高於現價，偏紅
    buy_color = DOWN_COLOR
    sell_color = UP_COLOR

    if depth_ratio >= 1.35:
        depth_status = "委買偏強"
        depth_color = buy_color
        depth_desc = "買方掛單支撐較明顯"

    elif depth_ratio <= 0.74:
        depth_status = "委賣偏強"
        depth_color = sell_color
        depth_desc = "賣方掛單壓力較明顯"

    else:
        depth_status = "委買委賣均衡"
        depth_color = WAIT_COLOR
        depth_desc = "買賣雙方暫時拉鋸"

    long_score = _safe_int(decision.get("long_score", 0))
    short_score = _safe_int(decision.get("short_score", 0))
    bias = _safe_int(decision.get("bias", long_score - short_score))

    force_total = max(long_score + short_score, 1)

    long_pct = int(long_score / force_total * 100)
    short_pct = int(short_score / force_total * 100)

    if bias >= 4:
        force_status = "多方優勢"
        force_color = UP_COLOR
        force_desc = "多方條件較完整"

    elif bias <= -4:
        force_status = "空方優勢"
        force_color = DOWN_COLOR
        force_desc = "空方壓力較明顯"

    else:
        force_status = "多空拉鋸"
        force_color = WAIT_COLOR
        force_desc = "等待方向確認"

    action = decision.get("action", "WAIT")
    score = _safe_int(decision.get("score", 0))
    rebound = _safe_int(decision.get("rebound", 0))
    rr = _fmt_value(decision.get("rr", "-"))
    fake_signal = decision.get("fake_signal", "NONE")

    if action == "BUY":
        action_text = "偏多觀察"
        action_color = UP_COLOR

    elif action == "SELL":
        action_text = "偏空觀察"
        action_color = DOWN_COLOR

    else:
        action_text = "等待訊號"
        action_color = WAIT_COLOR

    if fake_signal == "FAKE_BREAKOUT":
        fake_text = "疑似假突破"
        fake_color = WAIT_COLOR

    elif fake_signal == "FAKE_BREAKDOWN":
        fake_text = "疑似假跌破"
        fake_color = WAIT_COLOR

    elif fake_signal == "REAL_BREAKOUT":
        fake_text = "有效突破"
        fake_color = UP_COLOR

    elif fake_signal == "REAL_BREAKDOWN":
        fake_text = "有效跌破"
        fake_color = DOWN_COLOR

    else:
        fake_text = "無明顯假訊號"
        fake_color = SUBTEXT

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

    st.markdown("### 📊 市場深度 / 多空結構")

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
            grid-template-columns: 1.12fr 0.88fr;
            grid-template-rows: auto auto;
            gap: 9px;
            width: 100%;
            box-sizing: border-box;
        }}

        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 14px;
            padding: 10px;
            box-sizing: border-box;
            width: 100%;
            min-height: 126px;
        }}

        .card-title-row {{
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

        .tag {{
            font-size: 11px;
            font-weight: 900;
            border-radius: 999px;
            padding: 3px 8px;
            border: 1px solid currentColor;
            white-space: nowrap;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}

        th {{
            color: {SUBTEXT};
            font-size: 10.8px;
            font-weight: 800;
            padding: 4px 3px;
            border-bottom: 1px solid rgba(255,255,255,0.12);
        }}

        td {{
            font-size: 12.2px;
            font-weight: 900;
            text-align: center;
            padding: 4px 3px;
            border-bottom: 1px solid rgba(255,255,255,0.055);
        }}

        .buy-size,
        .buy-price {{
            color: {buy_color};
        }}

        .sell-price,
        .sell-size {{
            color: {sell_color};
        }}

        .force-status {{
            color: {force_color};
            font-size: 22px;
            font-weight: 900;
            line-height: 1;
            margin-top: 2px;
        }}

        .desc {{
            color: {SUBTEXT};
            font-size: 11.2px;
            margin-top: 5px;
            line-height: 1.35;
        }}

        .force-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
            margin-bottom: 6px;
        }}

        .long {{
            color: {UP_COLOR};
            font-size: 12.5px;
            font-weight: 900;
        }}

        .short {{
            color: {DOWN_COLOR};
            font-size: 12.5px;
            font-weight: 900;
        }}

        .bar {{
            width: 100%;
            height: 12px;
            background: rgba(255,255,255,0.10);
            border-radius: 999px;
            overflow: hidden;
            display: flex;
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

        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
            margin-top: 8px;
        }}

        .stat-grid-2 {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
            margin-top: 8px;
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
            line-height: 1.15;
        }}

        .main-status {{
            color: {depth_color};
            font-size: 20px;
            font-weight: 900;
            line-height: 1;
            margin-top: 4px;
        }}

        .tech-status {{
            color: {action_color};
            font-size: 20px;
            font-weight: 900;
            line-height: 1;
            margin-top: 4px;
        }}

        .note {{
            margin-top: 8px;
            padding-top: 7px;
            border-top: 1px solid rgba(255,255,255,0.08);
            color: {SUBTEXT};
            font-size: 11px;
            line-height: 1.35;
        }}

        @media (max-width: 900px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>

<body>
    <div class="grid">

        <div class="card">
            <div class="card-title-row">
                <div class="title">五檔報價</div>
                <div class="tag" style="color:{depth_color};">{depth_status}</div>
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
        </div>

        <div class="card">
            <div class="card-title-row">
                <div class="title">即時多空力道</div>
                <div class="tag" style="color:{force_color};">{force_status}</div>
            </div>

            <div class="force-status">{force_status}</div>
            <div class="desc">{force_desc}</div>

            <div class="force-row">
                <div class="long">多方 {long_score}</div>
                <div class="short">空方 {short_score}</div>
            </div>

            <div class="bar">
                <div class="long-bar"></div>
                <div class="short-bar"></div>
            </div>

            <div class="stat-grid-2">
                <div class="box">
                    <div class="box-label">多空差距</div>
                    <div class="box-value" style="color:{force_color};">{bias}</div>
                </div>

                <div class="box">
                    <div class="box-label">多方占比</div>
                    <div class="box-value" style="color:{UP_COLOR};">{long_pct}%</div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-title-row">
                <div class="title">委買委賣統計</div>
                <div class="tag" style="color:{depth_color};">{depth_status}</div>
            </div>

            <div class="main-status">{depth_status}</div>
            <div class="desc">{depth_desc}</div>

            <div class="stat-grid">
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
            <div class="card-title-row">
                <div class="title">技術狀態</div>
                <div class="tag" style="color:{action_color};">{escape(action_text)}</div>
            </div>

            <div class="tech-status">{escape(action_text)}</div>
            <div class="desc">依交易決策、反彈機率、假突破訊號綜合判斷。</div>

            <div class="stat-grid-2">
                <div class="box">
                    <div class="box-label">Score</div>
                    <div class="box-value" style="color:{action_color};">{score}</div>
                </div>

                <div class="box">
                    <div class="box-label">反彈率</div>
                    <div class="box-value" style="color:{WAIT_COLOR};">{rebound}%</div>
                </div>

                <div class="box">
                    <div class="box-label">RR</div>
                    <div class="box-value" style="color:{action_color};">{escape(rr)}</div>
                </div>

                <div class="box">
                    <div class="box-label">假訊號</div>
                    <div class="box-value" style="color:{fake_color};font-size:12.5px;">{escape(fake_text)}</div>
                </div>
            </div>
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=292,
        scrolling=False,
    )
