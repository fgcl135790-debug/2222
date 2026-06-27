import streamlit as st
import pandas as pd

from backtest_engine import BacktestEngine
from win_rate_engine import WinRateEngine


def _fmt_pct(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def _fmt_num(value):
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "-"


def render_backtest_sidebar_panel(api_key, stock_code):
    with st.sidebar.expander("📊 回測", expanded=False):

        st.caption("使用 Fugle 歷史分 K 回測目前策略。")

        if not api_key:
            st.warning("請先輸入 Fugle API KEY。")
            return

        symbol = st.text_input(
            "回測股票",
            value=str(stock_code),
            key="bt_symbol",
        )

        timeframe = st.selectbox(
            "K 線週期",
            options=["1", "5", "15", "30"],
            index=0,
            format_func=lambda x: f"{x} 分K",
            key="bt_timeframe",
        )

        score_threshold = st.slider(
            "最低 Score",
            min_value=50,
            max_value=95,
            value=75,
            step=5,
            key="bt_score_threshold",
        )

        require_resonance = st.checkbox(
            "只測多週期共振",
            value=True,
            key="bt_require_resonance",
        )

        avoid_open_minutes = st.slider(
            "避開開盤前幾分鐘",
            min_value=0,
            max_value=30,
            value=15,
            step=5,
            key="bt_avoid_open",
        )

        max_hold_bars = st.slider(
            "最多持有 K 數",
            min_value=10,
            max_value=90,
            value=45,
            step=5,
            key="bt_max_hold_bars",
        )

        run_clicked = st.button(
            "執行回測",
            use_container_width=True,
            key="bt_run",
        )

        if run_clicked:
            st.info("已收到回測指令，開始抓歷史 K 線...")

            try:
                with st.spinner("回測中，請稍等..."):
                    result = BacktestEngine.run(
                        api_key=api_key,
                        symbol=symbol,
                        timeframe=timeframe,
                        score_threshold=score_threshold,
                        require_resonance=require_resonance,
                        avoid_open_minutes=avoid_open_minutes,
                        max_hold_bars=max_hold_bars,
                    )

                st.session_state.backtest_result = result

                if result.get("ok"):
                    st.success("回測完成")
                else:
                    st.error(result.get("message", "回測失敗"))

            except Exception as e:
                st.session_state.backtest_result = {
                    "ok": False,
                    "message": str(e),
                    "summary": {},
                    "trades": [],
                }

                st.error("回測執行時發生錯誤")
                st.exception(e)

        result = st.session_state.get("backtest_result")

        if not result:
            st.info("尚未執行回測。")
            return

        if not result.get("ok"):
            st.error(result.get("message", "回測失敗"))
            return

        summary = result.get("summary", {})
        trades = result.get("trades", [])

        st.divider()

        st.caption(
            f"{result.get('symbol')}｜{result.get('timeframe')}分K｜"
            f"{result.get('days')} 日｜{result.get('candles')} 根K"
        )

        c1, c2 = st.columns(2)

        with c1:
            st.metric("總交易", summary.get("total", 0))
            st.metric("勝率", _fmt_pct(summary.get("win_rate", 0)))
            st.metric("做多勝率", _fmt_pct(summary.get("buy_win_rate", 0)))

        with c2:
            st.metric("Profit Factor", _fmt_num(summary.get("profit_factor", 0)))
            st.metric("總報酬", _fmt_pct(summary.get("total_pnl", 0)))
            st.metric("做空勝率", _fmt_pct(summary.get("sell_win_rate", 0)))

        st.caption(
            f"最大回撤 {_fmt_pct(summary.get('max_drawdown', 0))}｜"
            f"最大連敗 {summary.get('max_consecutive_loss', 0)}"
        )

        if trades:
            import_clicked = st.button(
                "匯入勝率統計",
                use_container_width=True,
                key="bt_import_to_winrate",
            )

            if import_clicked:
                count = WinRateEngine.import_backtest_trades(
                    st=st,
                    trades=trades,
                )

                st.success(f"已匯入 {count} 筆回測交易到勝率統計")

            st.divider()
            st.caption("最近 10 筆回測交易")

            df = pd.DataFrame(trades[-10:])

            show_cols = [
                "date",
                "action",
                "score",
                "entry_time",
                "exit_time",
                "pnl_pct",
                "result",
            ]

            df = df[[col for col in show_cols if col in df.columns]]

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=230,
            )

            csv = pd.DataFrame(trades).to_csv(
                index=False,
                encoding="utf-8-sig",
            )

            st.download_button(
                "下載回測明細 CSV",
                data=csv,
                file_name=f"backtest_{symbol}_{timeframe}m.csv",
                mime="text/csv",
                use_container_width=True,
            )
