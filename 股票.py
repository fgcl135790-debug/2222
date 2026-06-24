import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, time
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
        
    # 將富果回傳的單筆成交股數 (volume / size) 換算成張數
    df['lots'] = df['volume'] / 1000.0
    
    # 根據價格穿透法初步判定內外盤
    df['type'] = np.where(df['price'] >= reference_price, '買盤進攻', '賣盤系統')
    
    # 嚴格篩選單筆張數大於等於門檻的大單
    large_df = df[df['lots'] >= large_threshold_lots].copy()
    
    buy_large_total = large_df[large_df['type'] == '買盤進攻']['lots'].sum()
    sell_large_total = large_df[large_df['type'] == '賣盤系統']['lots'].sum()
    
    # 累加至全域 Session State 以計算總體大戶拉鋸方向
    st.session_state.cumulative_buy_large += buy_large_total
    st.session_state.cumulative_sell_large += sell_large_total
    
    decision_text = "⚖️ 籌碼拉鋸中"
    if st.session_state.cumulative_buy_large > 0 and st.session_state.cumulative_sell_large > 0:
        ratio = st.session_state.cumulative_buy_large / st.session_state.cumulative_sell_large
        if ratio >= 1.5:
            decision_text = "🔥【🚀 做多訊號】買盤大戶強烈壓制"
        elif ratio <= 0.66:
            decision_text = "❄️【💥 做空訊號】賣盤大戶無情摜壓"
            
        # 1% 回撤安全清空籌碼標記邏輯
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

api_key_to_use = api_key # 相容舊變數
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

            # 模擬一條虛擬的即時成交 Tick 數據
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
            
            # 【總量修復】直接從最高層結構精準提取今日成交總量
            raw_volume = quote.get('total', {}).get('volume', 0)
            total_volume_lots = int(raw_volume / 1000) if raw_volume else 0

            raw_bids = quote.get('bids', [])
            raw_asks = quote.get('asks', [])
            bids = raw_bids if isinstance(raw_bids, list) else []
            asks = raw_asks if isinstance(raw_asks, list) else []
            while len(bids) < 5: bids.append({'price': 0.0, 'volume': 0})
            while len(asks) < 5: asks.append({'price': 0.0, 'volume': 0})

            # 【核心串接修復】利用 requests 備用直接撈取富果即時成交明細（Trades）端點
            try:
                url = f"https://fugle.tw{code}"
                headers = {"X-API-KEY": api_key} if api_key else {}
                res = requests.get(url, headers=headers, timeout=3)
                raw_trades_list = res.json().get('trades', []) if res.status_code == 200 else []
            except:
                raw_trades_list = []

            # 精準提煉現價
            last_trade_raw = quote.get('lastTrade', {})
            tick_price = last_trade_raw.get('price', 0.0) if isinstance(last_trade_raw, dict) else 0.0
            
            if tick_price and tick_price > 0:
                current_price = tick_price
            elif len(raw_trades_list) > 0:
                current_price = raw_trades_list[0].get('price', reference_price)
            else:
                current_price = quote.get('lastPrice', reference_price)

            trade_time = int(time_module.time() * 1000)

            # 將最新成交明細重組成大戶過濾器能辨識的格式
            if raw_trades_list:
                trades_data = []
                for t in raw_trades_list:
                    trades_data.append({
                        'price': t.get('price', current_price),
                        'volume': t.get('size', t.get('volume', 0)),
                        'time': t.get('time', trade_time)
                    })
            else:
                unit_val = last_trade_raw.get('size', last_trade_raw.get('unit', 0)) if isinstance(last_trade_raw, dict) else 0
                trades_data = [{'price': current_price, 'volume': unit_val, 'time': trade_time}] if current_price > 0.0 
             # ==============================================================================
        # 🎨 畫面獨立渲染、最少150張過濾與頻率保護防禦
        # ==============================================================================
        if current_price == 0.0 and not test_mode:
            st.warning("⏳ 目前無即時成交數據...")
            return

        ref_price_final = open_price if open_price > 0 else current_price
        
        # 這裡還原你原本設計的動態門檻變數（完全不動你的變數命名）
        large_threshold_lots = dynamic_threshold

        large_list, b_total, s_total, decision = process_large_orders(
            trades_data, large_threshold_lots, ref_price_final
        )
        
        t_bid_vol, t_ask_vol, imbalance, b_pow, a_pow = calculate_metrics(
            bids, asks, total_volume_lots, current_price
        )

        # ----------------------------------------------------------------------
        # ⚠️ 以下完全保留你原本最精美的網頁 HTML 表格與 Layout 渲染，一字不改 ⚠️
        # ----------------------------------------------------------------------
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
                st.caption(f"⏳ 暫無超過 {large_threshold_lots} 張之大戶特大單成交...")

    except Exception as e:
        st.error(f"系統執行發生異常: {str(e)}")

# ==============================================================================
# 7. 啟動 Streamlit 執行引擎
# ==============================================================================
start_streaming(code)
           
