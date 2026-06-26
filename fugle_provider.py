import requests


class FugleProvider:

    def __init__(

        self,

        api_key,

    ):

        self.api_key = api_key

        self.url = (
            "https://api.fugle.tw/marketdata/v1.0"
        )

    # =========================
    # 即時報價
    # =========================

    def get_quote(

        self,

        stock_no,

    ):

        endpoint = (

            f"{self.url}/intraday/quote"

        )

        params = {

            "symbol": stock_no,

        }

        headers = {

            "X-API-KEY": self.api_key,

        }

        response = requests.get(

            endpoint,

            params=params,

            headers=headers,

            timeout=10,

        )

        response.raise_for_status()

        data = response.json()["data"]

        quote = data.get(

            "quote",

            {}

        )

        order = data.get(

            "order",

            {}

        )

        trade = data.get(

            "trade",

            {}

        )

        # =========================
        # 基本資訊
        # =========================

        name = data.get(

            "info",

            {}

        ).get(

            "name",

            stock_no,

        )

        price = trade.get(

            "price",

            quote.get(

                "priceHigh",

                0,

            ),

        )

        if price is None:

            price = 0

        vwap = quote.get(

            "avgPrice",

            price,

        )

        if vwap is None:

            vwap = price

        volume = trade.get(

            "size",

            0,

        )

        if volume is None:

            volume = 0

        # =========================
        # Best5
        # =========================

        bids = order.get(

            "bids",

            []

        )

        asks = order.get(

            "asks",

            []

        )

        if bids is None:

            bids = []

        if asks is None:

            asks = []

        # 補滿五檔

        while len(bids) < 5:

            bids.append(

                {

                    "price": 0,

                    "size": 0,

                }

            )

        while len(asks) < 5:

            asks.append(

                {

                    "price": 0,

                    "size": 0,

                }

            )

        # =========================
        # 成交序號
        # =========================

        trade_serial = trade.get(

            "serial",

            trade.get(

                "at",

                0,

            ),

        )

        if trade_serial is None:

            trade_serial = 0

        # =========================
        # 收盤判斷
        # =========================

        is_close = quote.get(

            "isClose",

            False,

        )

        if is_close is None:

            is_close = False

        # =========================
        # 回傳統一格式
        # =========================

        return {

            "name": name,

            "price": float(price),

            "vwap": float(vwap),

            "last_size": int(volume),

            "bids": bids[:5],

            "asks": asks[:5],

            "trade": {

                "serial": trade_serial,

            },

            "is_close": is_close,

        }
