class AlertEngine:

    @staticmethod
    def build(
        decision,
        trade_alert,
        big_order_log,
    ):

        alerts = []

        action = decision.get("action", "WAIT")
        score = decision.get("score", 0)
        fake_signal = decision.get("fake_signal", "NONE")
        fake_text = decision.get("fake_text", "")
        bias = decision.get("bias", 0)

        # =========================
        # 進出場提醒
        # =========================

        trade_level = trade_alert.get("level", "WAIT")

        if trade_level == "DANGER":

            alerts.append({
                "level": "DANGER",
                "title": trade_alert.get("title", "風險警示"),
                "message": trade_alert.get("message", "-"),
            })

        elif trade_level == "SUCCESS":

            alerts.append({
                "level": "SUCCESS",
                "title": trade_alert.get("title", "達成目標"),
                "message": trade_alert.get("message", "-"),
            })

        elif trade_level == "ENTRY":

            alerts.append({
                "level": "ENTRY",
                "title": trade_alert.get("title", "進場提醒"),
                "message": trade_alert.get("message", "-"),
            })

        elif trade_level == "WARNING":

            alerts.append({
                "level": "WARNING",
                "title": trade_alert.get("title", "價格警示"),
                "message": trade_alert.get("message", "-"),
            })

        # =========================
        # 假突破 / 假跌破
        # =========================

        if fake_signal == "FAKE_BREAKOUT":

            alerts.append({
                "level": "WARNING",
                "title": "疑似假突破",
                "message": fake_text or "突破後量能不足，不建議追多。",
            })

        elif fake_signal == "FAKE_BREAKDOWN":

            alerts.append({
                "level": "WARNING",
                "title": "疑似假跌破",
                "message": fake_text or "跌破後量能不足，不建議追空。",
            })

        elif fake_signal == "REAL_BREAKOUT":

            alerts.append({
                "level": "INFO",
                "title": "有效突破觀察",
                "message": fake_text or "價格突破近期高點，可偏多觀察。",
            })

        elif fake_signal == "REAL_BREAKDOWN":

            alerts.append({
                "level": "INFO",
                "title": "有效跌破觀察",
                "message": fake_text or "價格跌破近期低點，可偏空觀察。",
            })

        # =========================
        # 主力大單
        # =========================

        if big_order_log:

            latest = big_order_log[-1]

            direction = latest.get("direction", "UNKNOWN")
            direction_text = latest.get("direction_text", "-")
            volume_lot = latest.get("volume_lot", "-")
            strength = latest.get("strength", "-")

            if direction == "BUY":

                alerts.append({
                    "level": "BUY",
                    "title": "主力大單偏多",
                    "message": f"{direction_text}，{volume_lot} 張，強度：{strength}",
                })

            elif direction == "SELL":

                alerts.append({
                    "level": "SELL",
                    "title": "主力大單偏空",
                    "message": f"{direction_text}，{volume_lot} 張，強度：{strength}",
                })

            else:

                alerts.append({
                    "level": "INFO",
                    "title": "主力大單出現",
                    "message": f"{direction_text}，{volume_lot} 張，強度：{strength}",
                })

        # =========================
        # 高信心決策
        # =========================

        if action == "BUY" and score >= 75:

            alerts.append({
                "level": "BUY",
                "title": "高信心多方訊號",
                "message": f"Decision Score {score}，多方差距 {bias}。",
            })

        elif action == "SELL" and score >= 75:

            alerts.append({
                "level": "SELL",
                "title": "高信心空方訊號",
                "message": f"Decision Score {score}，空方差距 {abs(bias)}。",
            })

        elif action == "WAIT":

            alerts.append({
                "level": "WAIT",
                "title": "目前觀望",
                "message": "系統尚未給出明確進場條件。",
            })

        # =========================
        # 沒有警示
        # =========================

        if not alerts:

            alerts.append({
                "level": "INFO",
                "title": "目前無重大警示",
                "message": "行情暫時沒有明顯異常。",
            })

        return alerts[:5]
