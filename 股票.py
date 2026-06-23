import sys
import time
import threading
# 註冊與導入群益 API 元件 (需先向群益申請並安裝元件)
import comtypes.client as cc

# 模擬全域狀態，用來存放自動抓到的最新數據
market_data = {
    '2409': {
        'open_price': 0.0,
        'vwap': 0.0,
        'total_bid_vol': 0, # 內盤(買方)總掛單
        'total_ask_vol': 0, # 外盤(賣方)總掛單
        'avg_tick_vol': 50  # 該股平時平均每筆成交張數
    }
}

# 1. 建立群益報價事件監聽類別
class SKQuoteLibEvents:
    def __init__(self):
        pass

    # 當券商伺服器「即時回傳五檔」時，這個函式會被自動觸發（免手Key！）
    def OnBest5(self, market_no, stock_idx, best_bid_price, best_bid_vol, best_ask_price, best_ask_vol):
        # 這裡會自動抓到五檔加總
        # 註：實際群益API會回傳陣列，此處簡化加總邏輯示意
        stock_code = "2409" # 假設這是訂閱的友達
        market_data[stock_code]['total_bid_vol'] = sum(best_bid_vol) if isinstance(best_bid_vol, list) else best_bid_vol
        market_data[stock_code]['total_ask_vol'] = sum(best_ask_vol) if isinstance(best_ask_vol, list) else best_ask_vol

    # 當券商伺服器「即時回傳最新一筆成交明細」時，自動觸發此函式
    def OnNotifyTicks(self, market_no, stock_idx, ptr, date, time_str, close, qty, bid, ask, buy_sell_gb):
        """
        buy_sell_gb: 群益API定義 1=外盤(紅字敲進), 2=內盤(綠字砸貨)
        close: 最新成交價
        qty: 本筆成交張數
        """
        stock_code = "2409"
        data = market_data[stock_code]
        
        # 自動初始化開盤價與計算即時均價 (VWAP)
        if data['open_price'] == 0.0:
            data['open_price'] = close
            data['vwap'] = close
            
        # 核心判斷：真假希望自動計算
        is_big_order = qty >= (data['avg_tick_vol'] * 3)
        
        print(f"\n⚡ [API 自動抓取] 友達(2409) 現價:{close} | 均價:{data['vwap']:.2f} | 本筆成交:{qty}張")
        
        # ---- 自動流向「真假希望」判斷引擎 ----
        if close < data['vwap'] or close < data['open_price']:
            if data['total_bid_vol'] > (data['total_ask_vol'] * 1.5) and buy_sell_gb == 2 and is_big_order:
                print("🚨 判斷結果：【假希望】！外掛大單，明細卻一直內盤倒貨，快逃！")
        else:
            if buy_sell_gb == 1 and is_big_order:
                if data['total_ask_vol'] > (data['total_bid_vol'] * 1.3):
                    print("🔥 判斷結果：【真希望】！主力正在連續吃掉外盤大壓單，準備噴發！")
                else:
                    print("📈 判斷結果：【轉強】外盤有連續大單進場。")

# 2. 初始化群益 API 連線的主程式
def start_sk_api():
    print("🔄 正在初始化群益 API 並登入伺服器...")
    # 初始化群益元件 (需在 Windows 環境執行)
    try:
        sk_center = cc.CreateObject("SKCenterLib.SKCenterLib")
        sk_quote = cc.CreateObject("SKQuoteLib.SKQuoteLib")
        
        # 登入你的群益帳號 (身分證字號, 密碼)
        # login_code = sk_center.SKCenterLib_Login("YOUR_ID", "YOUR_PASSWORD")
        
        # 綁定即時監聽事件
        events = SKQuoteLibEvents()
        quote_events = cc.GetEvents(sk_quote, events)
        
        # 連線至報價伺服器
        # sk_quote.SKQuoteLib_EnterMonitor()
        
        # 自動訂閱友達 (2409) 的即時 Tick 與 五檔
        print("📡 成功訂閱 2409 友達 即時數據流，程式開始24小時自動監控...")
        
        # 讓程式持續維持連線監聽狀態
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"❌ 串接失敗，請確認是否安裝群益 API 元件。錯誤訊息: {e}")

if __name__ == "__main__":
    start_sk_api()
