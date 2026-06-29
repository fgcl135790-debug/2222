class TradeManagementEngine:
    """
    進場後管理 v1。
    回測與實戰提示用，不使用未來資料做進場判斷。

    回測中只在進場後逐根 K 判斷是否該提前退出：
    - 進場後若 5 根 K 仍沒有正向推進，先退出，避免小虧變停損。
    - 浮盈達 0.75% 後啟動保護，若回吐到保護線先退出。
    - 連續反向 K 也可提前退出。
    """

    @staticmethod
    def _f(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def check_exit(
        action,
        entry_price,
        current_candle,
        bars_held,
        best_favorable_pct=0.0,
        no_progress_bars=5,
        min_progress_pct=0.18,
        protect_after_pct=0.75,
        protect_floor_pct=0.12,
    ):
        action = str(action or "").upper()
        entry_price = max(TradeManagementEngine._f(entry_price), 0.000001)
        close = TradeManagementEngine._f(current_candle.get("close"), entry_price)
        high = TradeManagementEngine._f(current_candle.get("high"), close)
        low = TradeManagementEngine._f(current_candle.get("low"), close)
        open_price = TradeManagementEngine._f(current_candle.get("open"), close)

        if action == "BUY":
            current_pnl = (close - entry_price) / entry_price * 100
            intrabar_best = (high - entry_price) / entry_price * 100
            intrabar_worst = (low - entry_price) / entry_price * 100
            reverse_candle = close < open_price and close < (high + low) / 2
        elif action == "SELL":
            current_pnl = (entry_price - close) / entry_price * 100
            intrabar_best = (entry_price - low) / entry_price * 100
            intrabar_worst = (entry_price - high) / entry_price * 100
            reverse_candle = close > open_price and close > (high + low) / 2
        else:
            return None

        best_favorable_pct = max(best_favorable_pct, intrabar_best)

        # 5 根內沒有推動，且目前轉弱，就不要硬等停損。
        if bars_held >= no_progress_bars and best_favorable_pct < min_progress_pct and current_pnl <= -0.12:
            return {
                "exit": True,
                "reason": "進場後未推進，提早退出",
                "exit_price": close,
                "best_favorable_pct": best_favorable_pct,
                "current_pnl_pct": current_pnl,
            }

        # 浮盈保護：有走出來後不讓好單回吐成虧損太多。
        if best_favorable_pct >= protect_after_pct and current_pnl <= protect_floor_pct:
            return {
                "exit": True,
                "reason": "浮盈回吐保護",
                "exit_price": close,
                "best_favorable_pct": best_favorable_pct,
                "current_pnl_pct": current_pnl,
            }

        # 方向剛錯，且反向 K 明確，就先走。
        if bars_held >= 3 and reverse_candle and current_pnl <= -0.28 and intrabar_worst <= -0.35:
            return {
                "exit": True,
                "reason": "反向K棒提早停損",
                "exit_price": close,
                "best_favorable_pct": best_favorable_pct,
                "current_pnl_pct": current_pnl,
            }

        return {
            "exit": False,
            "best_favorable_pct": best_favorable_pct,
            "current_pnl_pct": current_pnl,
        }
