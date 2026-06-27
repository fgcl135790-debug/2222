import streamlit as st
import streamlit.components.v1 as components


def render_orderbook(bids, asks):

    st.subheader("📋 五檔")

    bids = bids[:5]
    asks = asks[:5]

    while len(bids) < 5:
        bids.append({"price": 0, "size": 0})

    while len(asks) < 5:
        asks.append({"price": 0, "size": 0})

    buy_prices = [float(x.get("price", 0)) for x in bids]
    buy_sizes = [int(x.get("size", 0)) for x in bids]

    sell_prices = [float(x.get("price", 0)) for x in asks]
    sell_sizes = [int(x.get("size", 0)) for x in asks]

    html = """
    <style>
    table{
        width:100%;
        border-collapse:collapse;
        font-size:13px;
    }

    th{
        color:#aaa;
        padding:8px;
        border-bottom:1px solid #333;
        text-align:center;
    }

    td{
        padding:8px;
        text-align:center;
        border-bottom:1px solid #222;
    }

    .buy{
        color:#00e676;
        font-weight:600;
    }

    .sell{
        color:#ff5252;
        font-weight:600;
    }

    </style>

    <table>

    <tr>
        <th>買量</th>
        <th>買價</th>
        <th>賣價</th>
        <th>賣量</th>
    </tr>
    """

    for i in range(5):

        html += f"""
        <tr>
            <td class="buy">{buy_sizes[i]}</td>
            <td class="buy">{buy_prices[i]}</td>
            <td class="sell">{sell_prices[i]}</td>
            <td class="sell">{sell_sizes[i]}</td>
        </tr>
        """

    html += "</table>"

    components.html(
        html,
        height=260,
        scrolling=False
    )
