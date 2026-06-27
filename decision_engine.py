class DecisionEngine:

    @staticmethod
    def generate(ai, price):

        score = ai["score"]

        rebound = ai["rebound_prob"]

        signal = ai["signal"]

        # ------------------------

        if signal == "BUY":

            action = "BUY"

            entry = f"{price-2:.1f} ~ {price+2:.1f}"

            stop = round(price * 0.996, 1)

            target = round(price * 1.008, 1)

        elif signal == "SELL":

            action = "SELL"

            entry = f"{price-2:.1f} ~ {price+2:.1f}"

            stop = round(price * 1.004, 1)

            target = round(price * 0.992, 1)

        else:

            action = "WAIT"

            entry = "-"

            stop = "-"

            target = "-"

        return {

            "action": action,

            "score": score,

            "entry": entry,

            "stop_loss": stop,

            "take_profit": target,

            "rr": "1 : 2",

            "rebound": rebound,

            "reasons": [

                f"AI信心 {score}%",

                f"反彈率 {rebound}%",

                ai["market_state"]

            ]

        }
