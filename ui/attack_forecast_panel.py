import streamlit as st
from html import escape

from ui.html_utils import render_html
from ui.theme import UP_COLOR, DOWN_COLOR, WAIT_COLOR, CARD_BORDER, TEXT, SUBTEXT


def _fmt(value, suffix=""):
    try:
        return f"{float(value):.2f}{suffix}"
    except Exception:
        return "-"


def render_attack_forecast_panel(forecast):
    forecast = forecast or {}
    direction = str(forecast.get("direction", "WAIT"))
    score = int(max(0, min(100, float(forecast.get("score", 0) or 0))))
    urgency = str(forecast.get("urgency", "LOW"))

    if direction == "LONG":
        color = UP_COLOR
        badge = "多方預警"
    elif direction == "SHORT":
        color = DOWN_COLOR
        badge = "空方預警"
    else:
        color = WAIT_COLOR
        badge = "等待"

    urgency_text = {
        "HIGH": "高",
        "MEDIUM": "中",
        "LOW": "低",
    }.get(urgency, urgency)

    title = escape(str(forecast.get("title", "攻勢預判")))
    message = escape(str(forecast.get("message", "等待攻勢訊號。")))
    reasons = forecast.get("reasons", []) or []
    features = forecast.get("features", {}) or {}

    reason_html = ""
    for r in reasons[:4]:
        reason_html += f'<div class="reason">◆ {escape(str(r))}</div>'

    if not reason_html:
        reason_html = '<div class="reason">◆ 等待量價與五檔同步。</div>'

    degree = int(score * 3.6)

    st.markdown("### ⚡ 攻勢預判")

    html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
body {{ margin:0; padding:0; background:transparent; font-family:Arial, 'Microsoft JhengHei', sans-serif; color:{TEXT}; }}
.card {{ width:100%; box-sizing:border-box; background:linear-gradient(135deg, rgba(17,24,39,.98), rgba(9,14,24,.98)); border:1px solid {CARD_BORDER}; border-radius:15px; padding:12px; }}
.top {{ display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }}
.title {{ font-size:15px; font-weight:900; color:{color}; line-height:1.25; }}
.msg {{ color:{SUBTEXT}; font-size:11.5px; line-height:1.45; margin-top:3px; }}
.badge {{ border:1px solid {color}; color:{color}; border-radius:999px; padding:3px 9px; font-size:11px; font-weight:900; white-space:nowrap; }}
.bar {{ height:7px; border-radius:999px; background:rgba(255,255,255,.10); overflow:hidden; margin:10px 0 8px; }}
.fill {{ width:{score}%; height:100%; background:{color}; border-radius:999px; }}
.grid {{ display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:6px; margin-top:8px; }}
.box {{ background:rgba(255,255,255,.035); border:1px solid rgba(255,255,255,.055); border-radius:9px; padding:7px 6px; min-width:0; }}
.lab {{ color:{SUBTEXT}; font-size:10px; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.val {{ color:{TEXT}; font-size:14px; font-weight:900; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.reasons {{ margin-top:9px; border-top:1px solid rgba(255,255,255,.08); padding-top:8px; }}
.reason {{ color:{TEXT}; font-size:11px; line-height:1.45; margin:2px 0; }}
@media (max-width:760px) {{ .grid {{ grid-template-columns:repeat(2, minmax(0,1fr)); }} }}
</style>
</head>
<body>
<div class="card">
  <div class="top">
    <div>
      <div class="title">{title}</div>
      <div class="msg">{message}</div>
    </div>
    <div class="badge">{escape(badge)}｜{score}</div>
  </div>
  <div class="bar"><div class="fill"></div></div>
  <div class="grid">
    <div class="box"><div class="lab">緊急度</div><div class="val">{escape(urgency_text)}</div></div>
    <div class="box"><div class="lab">多方蓄勢</div><div class="val">{escape(str(features.get('long_score', '-')))}</div></div>
    <div class="box"><div class="lab">空方蓄勢</div><div class="val">{escape(str(features.get('short_score', '-')))}</div></div>
    <div class="box"><div class="lab">量能加速</div><div class="val">{_fmt(features.get('volume_acceleration'), 'x')}</div></div>
    <div class="box"><div class="lab">五檔傾斜</div><div class="val">{_fmt(features.get('book_imbalance'))}</div></div>
    <div class="box"><div class="lab">VWAP乖離</div><div class="val">{_fmt(features.get('vwap_gap'), '%')}</div></div>
  </div>
  <div class="reasons">{reason_html}</div>
</div>
</body>
</html>
"""
    render_html(html, height=270)
