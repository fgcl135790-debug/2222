import streamlit as st
import pandas as pd
from html import escape

from win_rate_engine import WinRateEngine
from ui.html_utils import render_html
from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    CARD_BG,
    CARD_BORDER,
    TEXT,
    SUBTEXT,
)


def _fmt_pct(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def _fmt_value(value):
    if value is None:
        return "-"
    return escape(str(value))


def _active_html(active):
    if not active:
        return f"""
        <div class="track empty">
            <div class="track-title">目前沒有追蹤中的訊號</div>
            <div class="track-sub">等待 BUY / SELL 訊號成立後開始統計。</div>
        </div>
        """

    action = str(active.get("action", "-")).upper()
    color = UP_COLOR if action == "BUY" else DOWN_COLOR if action == "SELL" else WAIT_COLOR
    action_text = "做多追蹤中" if action == "BUY" else "做空追蹤中" if action == "SELL" else "追蹤中"

    return f"""
    <div class="track" style="border-left-color:{color};">
        <div class="track-top">
            <div>
                <div class="track-title" style="color:{color};">{escape(action_text)}</div>
                <div class="track-sub">
                    進場 {_fmt_value(active.get('entry_price'))}｜
                    追蹤 {_fmt_value(active.get('bars_held', 0))} / {_fmt_value(active.get('max_hold_bars', 50))} 根K
                </div>
            </div>
            <div class="track-badge" style="color:{color}; border-color:{color};">{escape(action)}</div>
        </div>
        <div class="track-levels">
            <span>停損 {_fmt_value(active.get('stop_loss'))} ({_fmt_value(active.get('stop_loss_pct'))}%)</span>
            <span>停利 {_fmt_value(active.get('take_profit'))} ({_fmt_value(active.get('take_profit_pct'))}%)</span>
        </div>
    </div>
    """


def render_win_rate_panel():
    trades = st.session_state.get("winrate_trades", [])
    active = st.session_state.get("winrate_active_trade")
    summary = WinRateEngine.summarize(trades)

    total = summary.get("total", 0)
    wins = summary.get("wins", 0)
    losses = summary.get("losses", 0)
    flats = summary.get("flats", 0)
    win_rate = _fmt_pct(summary.get("win_rate", 0))
    buy_win_rate = _fmt_pct(summary.get("buy_win_rate", 0))
    sell_win_rate = _fmt_pct(summary.get("sell_win_rate", 0))
    total_pnl = _fmt_pct(summary.get("total_pnl", 0))

    active_block = _active_html(active)

    st.markdown("### 📊 勝率統計")

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
    }}

    .card {{
        width: 100%;
        box-sizing: border-box;
        background: linear-gradient(135deg, rgba(17,24,39,0.98), rgba(9,14,24,0.98));
        border: 1px solid {CARD_BORDER};
        border-radius: 15px;
        padding: 12px;
    }}

    .track {{
        border-left: 4px solid {WAIT_COLOR};
        border-radius: 11px;
        background: rgba(255,255,255,0.035);
        padding: 9px 10px;
        margin-bottom: 10px;
    }}

    .track.empty {{
        border-left-color: #60a5fa;
    }}

    .track-top {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 8px;
    }}

    .track-title {{
        color: {TEXT};
        font-size: 13px;
        font-weight: 900;
        line-height: 1.25;
    }}

    .track-sub {{
        color: {SUBTEXT};
        font-size: 11px;
        margin-top: 3px;
        line-height: 1.35;
    }}

    .track-badge {{
        border: 1px solid;
        border-radius: 999px;
        padding: 2px 8px;
        font-size: 10.5px;
        font-weight: 900;
        white-space: nowrap;
    }}

    .track-levels {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 6px;
        margin-top: 8px;
        color: {SUBTEXT};
        font-size: 10.8px;
    }}

    .track-levels span {{
        background: rgba(255,255,255,0.035);
        border-radius: 8px;
        padding: 6px;
        text-align: center;
    }}

    .stats {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 7px;
    }}

    .stat {{
        background: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.055);
        border-radius: 10px;
        padding: 8px 6px;
        min-width: 0;
    }}

    .label {{
        color: {SUBTEXT};
        font-size: 10.5px;
        font-weight: 800;
        margin-bottom: 3px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .value {{
        color: {TEXT};
        font-size: 18px;
        font-weight: 900;
        line-height: 1.05;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .up {{ color: {UP_COLOR}; }}
    .down {{ color: {DOWN_COLOR}; }}
    .wait {{ color: {WAIT_COLOR}; }}

    @media (max-width: 760px) {{
        .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        .track-levels {{ grid-template-columns: 1fr; }}
        .value {{ font-size: 17px; }}
    }}
</style>
</head>
<body>
    <div class="card">
        {active_block}

        <div class="stats">
            <div class="stat">
                <div class="label">總筆數</div>
                <div class="value">{total}</div>
            </div>
            <div class="stat">
                <div class="label">勝率</div>
                <div class="value wait">{win_rate}</div>
            </div>
            <div class="stat">
                <div class="label">勝 / 敗 / 平</div>
                <div class="value">{wins} / {losses} / {flats}</div>
            </div>
            <div class="stat">
                <div class="label">做多勝率</div>
                <div class="value up">{buy_win_rate}</div>
            </div>
            <div class="stat">
                <div class="label">做空勝率</div>
                <div class="value down">{sell_win_rate}</div>
            </div>
            <div class="stat">
                <div class="label">總報酬</div>
                <div class="value wait">{total_pnl}</div>
            </div>
        </div>
    </div>
</body>
</html>
"""

    render_html(html, height=250)

    left, right = st.columns([1, 1], gap="small")

    with left:
        reset_clicked = st.button(
            "清空勝率統計",
            use_container_width=True,
            key="winrate_main_reset",
        )

    with right:
        if trades:
            csv = pd.DataFrame(trades).to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                "下載 CSV",
                data=csv,
                file_name="winrate_stats.csv",
                mime="text/csv",
                use_container_width=True,
                key="winrate_main_download",
            )
        else:
            st.button(
                "下載 CSV",
                use_container_width=True,
                disabled=True,
                key="winrate_main_download_disabled",
            )

    if reset_clicked:
        WinRateEngine.reset(st)
        st.success("勝率統計已清空")
        st.rerun()

    if trades:
        with st.expander("最近 10 筆訊號結果", expanded=False):
            df = pd.DataFrame(list(reversed(trades[-10:])))

            show_cols = [
                "source",
                "stock_code",
                "action",
                "exit_reason",
                "result",
                "pnl_pct",
                "score",
                "entry_time",
                "entry_price",
                "exit_time",
                "exit_price",
                "hold_bars",
                "stop_loss_pct",
                "take_profit_pct",
            ]

            df = df[[col for col in show_cols if col in df.columns]]

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=230,
            )
