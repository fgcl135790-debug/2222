from datetime import datetime


class MarketFlowEngine:
    """
    統一管理：
    1. quote 欄位格式
    2. 歷史資料 append
    3. price / volume / vwap / time 長度同步
    4. 換股清空
    5. K線、多週期、Decision 使用同一份資料
    """

    HISTORY_KEYS = [
        "price_history",
        "volume_history",
        "vwap_history",
        "time_history",
    ]

    STATE_DEFAULTS = {
        "price_history": [],
        "volume_history": [],
        "vwap_history": [],
        "time_history": [],
        "big_order_log": [],
        "tick": 0,
        "last_serial": None,
        "big_order_last_serial": None,
        "last_stock": None,
        "last_good_quote": None,
        "api_error_message": None,
    }

    @staticmethod
    def safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def safe_int(value, default=0):
        try:
            return int(round(float(value)))
        except Exception:
            return default

    @staticmethod
    def init_session_state(st):
        for key, default in MarketFlowEngine.STATE_DEFAULTS.items():
            if key not in st.session_state:
                if isinstance(default, list):
                    st.session_state[key] = []
                else:
                    st.session_state[key] = default

    @staticmethod
    def reset_market_state(st, keep_stock=None):
        st.session_state.price_history = []
        st.session_state.volume_history = []
        st.session_state.vwap_history = []
        st.session_state.time_history = []
        st.session_state.big_order_log = []
        st.session_state.tick = 0
        st.session_state.last_serial = None
        st.session_state.big_order_last_serial = None
        st.session_state.last_good_quote = None
        st.session_state.api_error_message = None

        if keep_stock is not None:
            st.session_state.last_stock = keep_stock

    @staticmethod
    def reset_if_stock_changed(st, stock_code):
        old_stock = st.session_state.get("last_stock", None)

        if old_stock != stock_code:
            MarketFlowEngine.reset_market_state(
                st=st,
                keep_stock=stock_code,
            )

    @staticmethod
    def normalize_quote(quote, stock_code, now=None):
        quote = quote or {}
        now = now or datetime.now()

        name = (
            quote.get("name")
            or quote.get("stock_name")
            or quote.get("symbolName")
            or stock_code
        )

        price = MarketFlowEngine.safe_float(
            quote.get("price")
            or quote.get("lastPrice")
            or quote.get("closePrice")
            or quote.get("close")
            or 0
        )

        vwap = MarketFlowEngine.safe_float(
            quote.get("vwap")
            or quote.get("avgPrice")
            or quote.get("averagePrice")
            or price
        )

        if vwap <= 0:
            vwap = price

        volume = MarketFlowEngine.safe_float(
            quote.get("last_size")
            or quote.get("lastSize")
            or quote.get("volume")
            or quote.get("size")
            or 0
        )

        high = MarketFlowEngine.safe_float(
            quote.get("high")
            or quote.get("highPrice")
            or price
        )

        low = MarketFlowEngine.safe_float(
            quote.get("low")
            or quote.get("lowPrice")
            or price
        )

        bids = quote.get("bids") or []
        asks = quote.get("asks") or []

        normalized_bids = MarketFlowEngine.normalize_levels(bids)
        normalized_asks = MarketFlowEngine.normalize_levels(asks)

        serial = (
            quote.get("serial")
            or quote.get("tick_id")
            or quote.get("tradeTime")
            or quote.get("time")
            or quote.get("date")
            or now.strftime("%H:%M:%S")
        )

        return {
            "name": name,
            "stock_code": stock_code,
            "price": price,
            "vwap": vwap,
            "volume": volume,
            "high": high,
            "low": low,
            "bids": normalized_bids,
            "asks": normalized_asks,
            "serial": str(serial),
            "raw": quote,
        }

    @staticmethod
    def normalize_levels(levels):
        result = []

        for item in levels or []:
            if not isinstance(item, dict):
                continue

            price = MarketFlowEngine.safe_float(
                item.get("price")
                or item.get("bid")
                or item.get("ask")
                or 0
            )

            size = MarketFlowEngine.safe_float(
                item.get("size")
                or item.get("volume")
                or item.get("qty")
                or 0
            )

            result.append(
                {
                    "price": price,
                    "size": size,
                }
            )

        while len(result) < 5:
            result.append(
                {
                    "price": 0,
                    "size": 0,
                }
            )

        return result[:5]

    @staticmethod
    def append_history(st, price, volume, vwap, now, serial, max_len=500):
        """
        只有 serial 改變才新增歷史資料。
        避免同一筆 quote 因為 Streamlit rerun 被重複 append。
        """

        if st.session_state.get("last_serial") == serial:
            return False

        st.session_state.last_serial = serial

        st.session_state.price_history.append(
            MarketFlowEngine.safe_float(price)
        )

        st.session_state.volume_history.append(
            MarketFlowEngine.safe_float(volume)
        )

        st.session_state.vwap_history.append(
            MarketFlowEngine.safe_float(vwap)
        )

        st.session_state.time_history.append(now)

        MarketFlowEngine.trim_and_align_history(
            st=st,
            max_len=max_len,
        )

        return True

    @staticmethod
    def trim_and_align_history(st, max_len=500):
        """
        保證四條歷史資料永遠一樣長。
        price / volume / vwap / time 只要其中一個短，就全部裁到最短。
        """

        for key in MarketFlowEngine.HISTORY_KEYS:
            if key not in st.session_state:
                st.session_state[key] = []

        lengths = [
            len(st.session_state.price_history),
            len(st.session_state.volume_history),
            len(st.session_state.vwap_history),
            len(st.session_state.time_history),
        ]

        min_len = min(lengths) if lengths else 0

        if min_len <= 0:
            st.session_state.price_history = []
            st.session_state.volume_history = []
            st.session_state.vwap_history = []
            st.session_state.time_history = []
            return

        min_len = min(min_len, max_len)

        st.session_state.price_history = st.session_state.price_history[-min_len:]
        st.session_state.volume_history = st.session_state.volume_history[-min_len:]
        st.session_state.vwap_history = st.session_state.vwap_history[-min_len:]
        st.session_state.time_history = st.session_state.time_history[-min_len:]

    @staticmethod
    def get_series(st):
        MarketFlowEngine.trim_and_align_history(st)

        return {
            "prices": st.session_state.price_history,
            "volumes": st.session_state.volume_history,
            "vwaps": st.session_state.vwap_history,
            "times": st.session_state.time_history,
        }

    @staticmethod
    def build_snapshot(st, quote, stock_code, now):
        q = MarketFlowEngine.normalize_quote(
            quote=quote,
            stock_code=stock_code,
            now=now,
        )

        MarketFlowEngine.append_history(
            st=st,
            price=q["price"],
            volume=q["volume"],
            vwap=q["vwap"],
            now=now,
            serial=q["serial"],
        )

        series = MarketFlowEngine.get_series(st)

        return {
            "quote": q,
            "name": q["name"],
            "stock_code": q["stock_code"],
            "price": q["price"],
            "vwap": q["vwap"],
            "volume": q["volume"],
            "high": q["high"],
            "low": q["low"],
            "bids": q["bids"],
            "asks": q["asks"],
            "serial": q["serial"],
            "prices": series["prices"],
            "volumes": series["volumes"],
            "vwaps": series["vwaps"],
            "times": series["times"],
        }
