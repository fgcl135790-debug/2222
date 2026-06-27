class WinRateEngine:
    @staticmethod
    def init_session_state(st):
        if "winrate_context_key" not in st.session_state:
            st.session_state.winrate_context_key = None

        if "winrate_active_trade" not in st.session_state:
            st.session_state.winrate_active_trade = None

        if "winrate_trades" not in st.session_state:
            st.session_state.winrate_trades = []

        if "winrate_last_signal_key" not in st.session_state:
            st.session_state.winrate_last_signal_key = None

    @staticmethod
    def reset(st):
        st.session_state.winrate_active_trade = None
        st.session_state.winrate_trades = []
        st.session_state.winrate_last_signal_key = None

    @staticmethod
    def reset_if_context_changed(st, stock_code, data_source, mode):
        context_key = f"{stock_code}|{data_source}|{mode}"

        if st.session_state.get("winrate_context_key") != context_key:
            st.session_state.winrate_context_key = context_key
            WinRateEngine.reset(st)

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(round(float(value)))
        except Exception:
            return default

    @staticmethod
    def _get_stop_take(action, entry_price, decision):
        stop_loss = WinRateEngine._safe_float(
            decision.get("stop_loss"),
            0,
        )

        take_profit = WinRateEngine._safe_float(
            decision.get("take_profit"),
            0,
        )

        if action == "BUY":
            if stop_loss <= 0 or stop_loss >= entry_price:
                stop_loss = entry_price * 0.994

            if take_profit <= entry_price:
                take_profit = entry_price * 1.010

        elif action == "SELL":
            if stop_loss <= entry_price:
                stop_loss = entry_price * 1.006

            if take_profit <= 0 or take_profit >= entry_price:
                take_profit = entry_price * 0.990

        return stop_loss, take_profit

    @staticmethod
    def update_live(
        st,
        stock_code,
        name,
        data_source,
        price,
        decision,
        now,
        min_score=75,
    ):
        action = decision.get("action", "WAIT")
        score = WinRateEngine._safe_int(decision.get("score", 0))

        price = WinRateEngine._safe_float(price)

        if price <= 0:
            return

        active = st.session_state.get("winrate_active_trade")

        # 先檢查現有交易是否出場
        if active is not None:
            active_action = active.get("action")
            entry_price = WinRateEngine._safe_float(active.get("entry_price"))
            stop_loss = WinRateEngine._safe_float(active.get("stop_loss"))
            take_profit = WinRateEngine._safe_float(active.get("take_profit"))

            exit_reason = None

            if active_action == "BUY":
                if price <= stop_loss:
                    exit_reason = "停損"
                elif price >= take_profit:
                    exit_reason = "停利"
                elif action == "SELL" and score >= min_score:
                    exit_reason = "反向訊號"

                pnl_pct = (price - entry_price) / entry_price * 100

            else:
                if price >= stop_loss:
                    exit_reason = "停損"
                elif price <= take_profit:
                    exit_reason = "停利"
                elif action == "BUY" and score >= min_score:
                    exit_reason = "反向訊號"

                pnl_pct = (entry_price - price) / entry_price * 100

            if exit_reason is not None:
                result = "WIN" if pnl_pct > 0 else "LOSS"

                if abs(pnl_pct) < 0.03:
                    result = "FLAT"

                trade = {
                    "source": data_source,
                    "stock_code": stock_code,
                    "name": name,
                    "action": active_action,
                    "entry_time": active.get("entry_time"),
                    "entry_price": round(entry_price, 2),
                    "exit_time": now.strftime("%H:%M:%S"),
                    "exit_price": round(price, 2),
                    "exit_reason": exit_reason,
                    "score": active.get("score"),
                    "pnl_pct": round(pnl_pct, 3),
                    "result": result,
                }

                st.session_state.winrate_trades.append(trade)
                st.session_state.winrate_active_trade = None

                if len(st.session_state.winrate_trades) > 300:
                    st.session_state.winrate_trades = st.session_state.winrate_trades[-300:]

                return

        # 沒有持倉時，才建立新交易
        if st.session_state.get("winrate_active_trade") is None:
            if action not in ["BUY", "SELL"]:
                return

            if score < min_score:
                return

            signal_key = f"{stock_code}|{data_source}|{action}|{score}|{now.strftime('%H:%M')}"

            if st.session_state.get("winrate_last_signal_key") == signal_key:
                return

            stop_loss, take_profit = WinRateEngine._get_stop_take(
                action=action,
                entry_price=price,
                decision=decision,
            )

            st.session_state.winrate_active_trade = {
                "source": data_source,
                "stock_code": stock_code,
                "name": name,
                "action": action,
                "entry_time": now.strftime("%H:%M:%S"),
                "entry_price": round(price, 2),
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "score": score,
            }

            st.session_state.winrate_last_signal_key = signal_key

    @staticmethod
    def import_backtest_trades(st, trades):
        if not trades:
            return 0

        imported = 0

        for trade in trades:
            item = dict(trade)
            item["source"] = "回測"
            st.session_state.winrate_trades.append(item)
            imported += 1

        if len(st.session_state.winrate_trades) > 300:
            st.session_state.winrate_trades = st.session_state.winrate_trades[-300:]

        return imported

    @staticmethod
    def summarize(trades):
        total = len(trades)

        wins = len([t for t in trades if t.get("result") == "WIN"])
        losses = len([t for t in trades if t.get("result") == "LOSS"])
        flats = len([t for t in trades if t.get("result") == "FLAT"])

        win_rate = wins / total * 100 if total else 0

        total_pnl = sum(
            WinRateEngine._safe_float(t.get("pnl_pct", 0))
            for t in trades
        )

        avg_pnl = total_pnl / total if total else 0

        buy_trades = [t for t in trades if t.get("action") == "BUY"]
        sell_trades = [t for t in trades if t.get("action") == "SELL"]

        buy_wins = len([t for t in buy_trades if t.get("result") == "WIN"])
        sell_wins = len([t for t in sell_trades if t.get("result") == "WIN"])

        buy_win_rate = buy_wins / len(buy_trades) * 100 if buy_trades else 0
        sell_win_rate = sell_wins / len(sell_trades) * 100 if sell_trades else 0

        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "flats": flats,
            "win_rate": win_rate,
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "buy_win_rate": buy_win_rate,
            "sell_win_rate": sell_win_rate,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
        }
