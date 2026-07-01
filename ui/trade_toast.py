import streamlit as st
from html import escape

from ui.html_utils import render_html
from ui.theme import UP_COLOR, DOWN_COLOR, WAIT_COLOR, TEXT, SUBTEXT


def _safe(value, default="-"):
    if value is None:
        return default
    text = str(value).strip()
    return escape(text if text else default)


def _style(event):
    level = str((event or {}).get("level", "warning")).lower()
    action = str((event or {}).get("action", "")).upper()
    event_type = str((event or {}).get("type", "")).upper()

    if level in ["success", "entry_buy"] or (event_type == "ENTRY" and action == "BUY"):
        return UP_COLOR, "做多"

    if level in ["danger", "entry_sell"] or (event_type == "ENTRY" and action == "SELL"):
        return DOWN_COLOR, "做空"

    return WAIT_COLOR, "提醒"


def render_trade_toast(event):
    if not event:
        return

    color, tag = _style(event)

    event_type = str(event.get("type", "ALERT")).upper()
    icon = "🚀" if event_type == "ENTRY" else "🔔"

    if event_type == "EXIT":
        icon = "🏁"
        tag = "出場"
    elif event_type == "ALERT":
        icon = "⚠️"

    title = _safe(event.get("title", "交易提醒"))
    message = _safe(event.get("message", ""))
    detail = _safe(event.get("detail", ""))
    created_at = _safe(event.get("created_at", ""), "")

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
        overflow: visible;
    }}

    .trade-toast {{
        position: fixed;
        top: 48px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 999999;
        width: min(560px, calc(100vw - 24px));
        pointer-events: none;
        box-sizing: border-box;
        background: rgba(10, 16, 28, 0.98);
        border: 1px solid {color};
        border-left: 6px solid {color};
        border-radius: 14px;
        box-shadow: 0 14px 35px rgba(0,0,0,0.45);
        color: {TEXT};
        display: grid;
        grid-template-columns: 34px 1fr auto;
        gap: 10px;
        align-items: center;
        padding: 10px 12px;
        animation: toast-life 6.2s ease forwards;
    }}

    .icon {{
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(255,255,255,0.06);
        font-size: 18px;
    }}

    .main {{ min-width: 0; }}

    .title {{
        color: {color};
        font-size: 15px;
        font-weight: 900;
        line-height: 1.25;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .message {{
        color: {TEXT};
        font-size: 12px;
        font-weight: 800;
        line-height: 1.35;
        margin-top: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .detail {{
        color: {SUBTEXT};
        font-size: 11px;
        line-height: 1.35;
        margin-top: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .tagbox {{
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 3px;
    }}

    .tag {{
        color: {color};
        border: 1px solid {color};
        border-radius: 999px;
        padding: 3px 8px;
        font-size: 11px;
        font-weight: 900;
        white-space: nowrap;
    }}

    .time {{
        color: {SUBTEXT};
        font-size: 10px;
        white-space: nowrap;
    }}

    @keyframes toast-life {{
        0% {{ opacity: 0; transform: translate(-50%, -12px); }}
        8% {{ opacity: 1; transform: translate(-50%, 0); }}
        78% {{ opacity: 1; transform: translate(-50%, 0); }}
        100% {{ opacity: 0; transform: translate(-50%, -18px); visibility: hidden; }}
    }}

    @media (max-width: 760px) {{
        .trade-toast {{
            top: 38px;
            width: calc(100vw - 18px);
            grid-template-columns: 30px 1fr;
            padding: 9px 10px;
            gap: 8px;
        }}

        .tagbox {{
            display: none;
        }}

        .icon {{ width: 30px; height: 30px; font-size: 16px; }}
        .title {{ font-size: 14px; }}
        .message {{ font-size: 11.5px; }}
    }}
</style>
</head>
<body>
    <div class="trade-toast">
        <div class="icon">{icon}</div>
        <div class="main">
            <div class="title">{title}</div>
            <div class="message">{message}</div>
            <div class="detail">{detail}</div>
        </div>
        <div class="tagbox">
            <div class="tag">{escape(tag)}</div>
            <div class="time">{created_at}</div>
        </div>
    </div>
</body>
</html>
"""

    render_html(html, height=120)
