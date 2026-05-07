import asyncio
import os
import requests
from binance import AsyncClient, BinanceSocketManager

# جلب الإعدادات من متغيرات البيئة (أمان عالي)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")

# إعدادات الحيتان
ICEBERG_THRESHOLD = 10.0 

def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram settings missing!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error: {e}")

async def whales_radar():
    client = await AsyncClient.create()
    bm = BinanceSocketManager(client)
    ms = bm.multiplex_socket([f'{SYMBOL.lower()}@depth10@100ms', f'{SYMBOL.lower()}@trade'])
    
    acc_buy_vol = 0
    current_ask_price = 0

    print(f"📡 Radar started for {SYMBOL}...")
    send_telegram_msg(f"✅ تم تشغيل رادار الحيتان على {SYMBOL}")

    async with ms as mscm:
        while True:
            res = await mscm.recv()
            stream = res['stream']
            data = res['data']

            if 'depth' in stream:
                current_ask_price = float(data['a'][0][0])

            elif 'trade' in stream:
                t_price = float(data['p'])
                t_qty = float(data['q'])
                is_buyer_maker = data['m']

                if not is_buyer_maker and t_price >= current_ask_price:
                    acc_buy_vol += t_qty
                    if acc_buy_vol >= ICEBERG_THRESHOLD:
                        msg = f"⚠️ **حوت يمتص السيولة!**\nالزوج: {SYMBOL}\nالسعر: {t_price}\nالكمية: {acc_buy_vol:.2f} BTC"
                        send_telegram_msg(msg)
                        acc_buy_vol = 0
                
                if t_price > current_ask_price:
                    acc_buy_vol = 0

if __name__ == "__main__":
    asyncio.run(whales_radar())
