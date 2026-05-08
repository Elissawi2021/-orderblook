import asyncio
import os
import requests
import sys
from binance import AsyncClient, BinanceSocketManager

# --- الإعدادات (ضع بياناتك هنا مباشرة) ---
TELEGRAM_TOKEN = "8774479062:AAH5bOscrF4HPp9eV2-v1GYTcvVST3Iq_PQ"
CHAT_ID = "690481231"
SYMBOL = "BTCUSDT"
ICEBERG_THRESHOLD = 150.0  # رفعناه لـ 150 لتقليل الضغط جداً

def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

async def whales_radar():
    client = await AsyncClient.create()
    # هنا السر: رفعنا الـ user_socket_buffer لـ 10000 لمنع الانفجار
    bm = BinanceSocketManager(client, user_socket_buffer=10000)
    ts = bm.trade_socket(SYMBOL)

    print(f"🚀 Whale Radar Started on {SYMBOL}...")
    
    async with ts as tscm:
        while True:
            try:
                res = await tscm.recv()
                if res and 'q' in res:
                    amount = float(res['q'])
                    if amount >= ICEBERG_THRESHOLD:
                        msg = f"🐳 *حوت جديد في السوق!*\nالكمية: {amount} BTC\nالسعر: {res['p']}"
                        send_telegram_msg(msg)
                        print(f"✅ تم إرسال تنبيه: {amount} BTC")
            except Exception as e:
                print(f"⚠️ خطأ مؤقت: {e}")
                await asyncio.sleep(1)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(whales_radar())
