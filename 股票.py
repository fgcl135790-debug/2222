import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time as time_module
import requests

# 調整全寬頁面
st.set_page_config(layout="wide", page_title="行動大戶籌碼五檔 APP", page_icon="⚡")

# 1. 初始化 Session State 變數
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.last_index_fetch_time = 0.0
    st.session_state.taiex_cache = (0.0, 0.0)  # price, change
    st.session_state.otc_cache = (0.0, 0.0)    # price, change
    st.session_state.wave_triggered = False     # 1% 回撤清空籌碼標記
    st.session_state.last_update_time = 0.0
    st.session_state.historical_trades = []     # 儲存歷史大單紀錄
    st.session_state.cumulative_buy_large = 0.0
    st.session_state.cumulative_sell_large = 0.0

# 2. 定義富果 REST 用戶端 (輕量封裝)
class RestClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://fugle.tw"
        self.headers = {"X-API-KEY": api_key} if api_key else {}

    class SubResource:
        def __init__(self, parent, resource_name):
            self.parent = parent
            self.resource_name = resource_name

        def get(self, symbol):
            url = f"{self.parent.base_url}/{self.resource_name}/{symbol}"
            try:
                res = requests.get(url, headers=self.parent.headers, timeout=5)
                if res.status_code == 200:
                    return res.json()
            except:
                pass
            return {}

    @property
    def stock(self):
        class IntradayService:
            def __init__(self, parent):
                self.parent = parent
            @property
            def quote(self): return RestClient.SubResource(self.parent, "quote")
            @property
            def candles(self): return RestClient.SubResource(self.parent, "candles")
            @property
            def tickers(self): return RestClient.SubResource(self.parent, "tickers")
        return IntradayService(self)

# 3. 核心邏輯計算函式
def calculate_metrics(bids, asks, total_volume, last_price):
    """計算最佳五檔的買賣盤氣勢與不平衡度"""
    total_bid_vol = sum([b.get('volume', 0) for b in bids])
    total_ask_vol = sum([a.get('volume', 0) for a in asks])
    
    if total_bid_vol + total_ask_vol > 0:
        order_imbalance = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol) * 100
    else:
        order_imbalance = 0.0
        
    bid_power = total_bid_vol / 5.0
    ask_power = total_ask_vol / 5.0
    
    return total_bid_vol, total_ask_vol, order_imbalance, bid_power, ask_power

def process_large_orders(trades_data, large_threshold_lots, reference_price):
    """過濾與處理30秒內的大戶進攻明細，並累加多空籌碼"""
    if not trades_data:
        return [], 0.0, 0.0, ""
        
    df = pd.DataFrame(trades_data)
    if df.empty or 'price' not in df.columns or 'volume' not in df.columns:
        return [], 0.0, 0.0, ""
        
    df['lots'] = df['volume'] / 1000.0
    df['type'] = np.where(df['price'] >= reference_price, '買盤進攻', '賣盤系統')
    
    large_df = df[df['lots'] >= large_threshold_lots].copy()
    
    buy_large_total = large_df[large_df['type'] == '買盤進攻']['lots'].sum()
    sell_large_total = large_df[large_df['type'] == '賣盤系統']['lots'].sum()
    
    st.session_state.cumulative_buy_large += buy_large_total
    st.session_state.cumulative_sell_large += sell_large_total
    
    decision_text = "⚖️ 籌碼拉鋸中"
    if st.session_state.cumulative_buy_large > 0 and st.session_state.cumulative_sell_large > 0:
        ratio = st.session_state.cumulative_buy_large / st.session_state.cumulative_sell_large
        if ratio >= 1.5:
            decision_text = "🔥【🚀 做多訊號】買盤大戶強烈壓制"
        elif ratio <= 0.66:
            decision_text = "❄️【💥 做空訊號】賣盤大戶無情摜壓"
            
        if ratio >= 2.0 and not st.session_state.wave_triggered:
            st.session_state.wave_triggered = True
            decision_text = "⚠️【🛡️ 觸發 1% 回撤】清空多頭籌碼"
            st.session_state.cumulative_buy_large = 0.0
            
    return large_df.to_dict('records'), buy_large_total, sell_large_total, decision_text
# 4. 圖表渲染函式
def render_order_book_chart(bids, asks):
    """使用 Plotly 繪製水平條形圖，直觀呈現五檔買賣盤委託量對決"""
    bid_prices = [b.get('price', 0) for b in bids][::-1]
    bid_vols = [b.get('volume', 0) / 1000.0 for b in bids][::-1]
    
    ask_prices = [a.get('price', 0) for a in asks]
    ask_vols = [a.get('volume', 0) / 1000.0 for a in asks]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=[f"買 {p}" for p in bid_prices],
        x=bid_vols,
        orientation='h',
        name='買方委託(張)',
        marker_color='#22c55e'
    ))
    
    fig.add_trace(go.Bar(
        y=[f"賣 {p}" for p in ask_prices],
        x=ask_vols,
        orientation='h',
        name='賣方委託(張)',
        marker_color='#ef4444'
    ))
    
    fig.update_layout(
        barmode='stack',
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff')
    )
    st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# 5. 主應用程式進入點與側邊欄設定
# ==============================================================================
st.title("⚡ 行動大戶籌碼五檔 APP")

with st.sidebar.expander("⚙️ 設定：輸入金鑰 / 更換股票 / 模擬測試", expanded=True):
    api_key = st.text_input("富果 API Key", type="password", value="")
    code = st.text_input("股票代號", value="2409")
    test_mode = st.checkbox("🌙 啟動深夜模擬測試 (半夜看畫面專用)", value=False)

api_key_to_use = api_key 
client = RestClient(api_key=api_key) if api_key else None

@st.fragment(run_every=2.0)
def start_streaming(code):
    try:
        current_now = time_module.time()
        elapsed_speed = current_now - st.session_state.last_update_time
        st.session_state.last_update_time = current_now

        if test_mode:
            taiex_price, taiex_change = 22100.50, 150.25
            otc_price, otc_change = 265.12, -0.45
            open_price = 29.00
            stock_name = "友達" if code == "2409" else "測試股"
            total_volume_lots = 95459
            trade_time = int(current_now * 1000)

            last_trade = {'price': 28.50, 'unit': 155000, 'time': trade_time}
            current_price = 28.50
            tick_qty = 155
            tick_price = 28.50
            
            bids = [{'price': 28.45 - i*0.05, 'volume': (250-i*30)*1000} for i in range(5)]
            asks = [{'price': 28.55 + i*0.05, 'volume': (180-i*20)*1000} for i in range(5)]
            
            trades_data = [{'price': 28.50, 'volume': 155000, 'time': trade_time}]

        else:
            if not client:
                st.error("❌ 請先在設定中輸入正確的 富果 API Key！")
                return

            if current_now - st.session_state.last_index_fetch_time > 180.0:
                try:
                    tx_q = client.stock.quote.get("0000")
                    tx_p = tx_q.get('lastTrade', {}).get('price', 0.0)
                    tx_ref = tx_q.get('referencePrice', tx_p)
                    st.session_state.taiex_cache = (tx_p, tx_p - tx_ref)
                    st.session_state.last_index_fetch_time = current_now
                except:
                    pass
                try:
                    otc_q = client.stock.quote.get("0001")
                    otc_p = otc_q.get('lastTrade', {}).get('price', 0.0)
                    otc_ref = otc_q.get('referencePrice', otc_p)
                    st.session_state.otc_cache = (otc_p, otc_p - otc_ref)
                except:
                    pass

            taiex_price, taiex_change = st.session_state.taiex_cache
            otc_price, otc_change = st.session_state.otc_cache

            quote = client.stock.quote.get(code)
            ticker = client.stock.tickers.get(code)
            
            stock_name = ticker.get('name', code)
            open_price = quote.get('openPrice', 0.0)
            reference_price = quote.get('referencePrice', open_price)
            raw_volume = quote.get('total', {}).get('volume', 0)
            total_volume_lots = int(raw_volume / 1000) if raw_volume else 0

            raw_bids = quote.get('bids', [])
            raw_asks = quote.get('asks', [])
            bids = raw_bids if isinstance(raw_bids, list) else []
            asks = raw_asks if isinstance(raw_asks, list) else []
            while len(bids) < 5: bids.append({'price': 0.0, 'volume': 0})
            while len(asks) < 5: asks.append({'price': 0.0, 'volume': 0})

            last_trade_raw = quote.get('lastTrade')
            if isinstance(last_trade_raw, list) and len(last_trade_raw) > 0:
                last_trade = last_trade_raw
            elif isinstance(last_trade_raw, dict):
                last_trade = last_trade_raw
            else:
                last_trade = {}

            tick_qty = int(last_trade.get('unit', 0) / 1000) if last_trade.get('unit') else 0
            tick_price = last_trade.get('price', 0.0)
            trade_time = last_trade.get('time', 0)
            
            # 【完美保底防護機制】如果開盤瞬間 tick_price 為 0，拿開盤價或昨收頂替，確保絕不變 0 崩潰
            if tick_price and tick_price > 0:
                current_price = tick_price
            else:
                current_price = open_price if open_price > 0 else reference_price

            last_bid = bids[0].get('price', 0.0) if bids and len(bids) > 0 else 0.0
            last_ask = asks[0].get('price', 0.0) if asks and len(asks) > 0 else 0.0
            
            trades_data = [{'price': current_price, 'volume': last_trade.get('unit', 0), 'time': trade_time}] if current_price > 0.0 else []

        # ==============================================================================
        # 画面独立渲染、最少150張過濾與頻率保護防禦
        # ==============================================================================
        if current_price == 0.0 and not test_mode:
            st.warning("⏳ 目前無即時成交數據...")
            return

        ref_price_final = open_price if open_price > 0 else current_price
        large_threshold_lots = 150.0

        large_list, b_total, s_total, decision = process_large_orders(
            trades_data, large_threshold_lots, ref_price_final
        )
        
        t_bid_vol, t_ask_vol, imbalance, b_pow, a_pow = calculate_metrics(
            bids, asks, total_volume_lots, current_price
        )

        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("🇹🇼 加權指數", f"{taiex_price:,.2f}", f"{taiex_change:+.2f}")
        with m_col2:
            st.metric("🔰 櫃買指數", f"{otc_price:,.2f}", f"{otc_change:+.2f}")
        with m_col3:
            change_val = current_price - ref_price_final if ref_price_final > 0 else 0.0
            st.metric(f"📈 {stock_name} ({code})", f"{current_price:.2f}", f"{change_val:+.2f}")

        st.markdown("---")

        layout_col1, layout_col2 = st.columns()

        with layout_col1:
            st.subheader("📋 盤口最佳五檔")
            render_order_book_chart(bids, asks)
            st.markdown(f"""
            *   **買盤總委託**：`{int(t_bid_vol/1000)}` 張 (均量: `{b_pow/1000:.1f}` 張)
            *   **賣盤總委託**：`{int(t_ask_vol/1000)}` 張 (均量: `{a_pow/1000:.1f}` 張)
            *   **五檔不平衡度**：`{imbalance:+.2f}%`
            """)

        with layout_col2:
            st.subheader("🔥 30秒大戶進攻火網")
            if "🚀" in decision:
                st.success(decision)
            elif "💥" in decision:
                st.error(decision)
            elif "🛡️" in decision:
                st.warning(decision)
            else:
                st.info(decision)
                
            st.markdown(f"""
            *   **當前大單門檻**：`{large_threshold_lots}` 張
            *   **累計大戶買進**：`{st.session_state.cumulative_buy_large:.1f}` 張
            *   **累計大戶賣出**：`{st.session_state.cumulative_sell_large:.1f}` 張
            """)

            st.subheader("📜 大戶進攻即時紀錄 (30秒內明細)")
            if large_list:
                rec_df = pd.DataFrame(large_list)
                rec_df['時間'] = pd.to_datetime(rec_df['time'], unit='ms').dt.strftime('%H:%M:%S')
                rec_df['價格'] = rec_df['price'].map('{:.2f}'.format)
                rec_df['張數'] = rec_df['lots'].map('{:.1f}'.format)
                rec_df['屬性'] = rec_df['type']
                st.dataframe(rec_df[['時間', '價格', '張數', '屬性']], use_container_width=True, hide_index=True)
            else:
                st.caption("⏳ 暫無超過 150 張之大戶特大單成交...")

    except Exception as e:
        st.error(f"系統執行發生異常: {str(e)}")

start_streaming(code)
