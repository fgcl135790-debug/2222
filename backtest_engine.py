    @staticmethod
    def _simulate_exit(
        action,
        entry_price,
        entry_index,
        day_candles,
        decision,
        max_hold_bars=45,
        default_stop_pct=0.6,
        default_take_pct=1.0,
    ):
        stop_loss = BacktestEngine._safe_float(
            decision.get("stop_loss"),
            0,
        )

        take_profit = BacktestEngine._safe_float(
            decision.get("take_profit"),
            0,
        )

        default_stop_pct = BacktestEngine._safe_float(default_stop_pct, 0.6)
        default_take_pct = BacktestEngine._safe_float(default_take_pct, 1.0)

        stop_rate = default_stop_pct / 100
        take_rate = default_take_pct / 100

        # 如果 DecisionEngine 沒給合理停損停利，就用 UI 設定的固定百分比
        if action == "BUY":
            if stop_loss <= 0 or stop_loss >= entry_price:
                stop_loss = entry_price * (1 - stop_rate)

            if take_profit <= entry_price:
                take_profit = entry_price * (1 + take_rate)

            stop_loss_pct = (entry_price - stop_loss) / entry_price * 100
            take_profit_pct = (take_profit - entry_price) / entry_price * 100

        elif action == "SELL":
            if stop_loss <= entry_price:
                stop_loss = entry_price * (1 + stop_rate)

            if take_profit <= 0 or take_profit >= entry_price:
                take_profit = entry_price * (1 - take_rate)

            stop_loss_pct = (stop_loss - entry_price) / entry_price * 100
            take_profit_pct = (entry_price - take_profit) / entry_price * 100

        else:
            stop_loss_pct = 0
            take_profit_pct = 0

        exit_price = entry_price
        exit_reason = "時間出場"
        exit_index = min(
            len(day_candles) - 1,
            entry_index + max_hold_bars,
        )

        end_index = min(
            len(day_candles) - 1,
            entry_index + max_hold_bars,
        )

        for i in range(entry_index + 1, end_index + 1):
            c = day_candles[i]
            high = BacktestEngine._safe_float(c.get("high"))
            low = BacktestEngine._safe_float(c.get("low"))
            close = BacktestEngine._safe_float(c.get("close"))

            if action == "BUY":
                # 同一根同時碰停損停利時，保守視為先停損
                if low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "停損"
                    exit_index = i
                    break

                if high >= take_profit:
                    exit_price = take_profit
                    exit_reason = "停利"
                    exit_index = i
                    break

            elif action == "SELL":
                if high >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "停損"
                    exit_index = i
                    break

                if low <= take_profit:
                    exit_price = take_profit
                    exit_reason = "停利"
                    exit_index = i
                    break

            exit_price = close
            exit_index = i

        if action == "BUY":
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        result = "WIN" if pnl_pct > 0 else "LOSS"

        if abs(pnl_pct) < 0.03:
            result = "FLAT"

        hold_bars = max(0, exit_index - entry_index)

        return {
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "exit_index": exit_index,
            "pnl_pct": pnl_pct,
            "result": result,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "hold_bars": hold_bars,
            "max_hold_bars": max_hold_bars,
        }
