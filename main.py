import asyncio
import os
import requests
import sys
from binance import AsyncClient, BinanceSocketManager

# --- الإعدادات (تُجلب من Environment Variables في السيرفر) ---
TELEGRAM_TOKEN = os.getenv("8774479062:AAH5bOscrF4HPp9eV2-v1GYTcvVST3Iq_PQ")
CHAT_ID = os.getenv("690481231")
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
# اسم السيرفر لتعرف من أرسل التنبيه (مثلاً: Render-Frankfurt أو Google-Cloud)
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "Whale-Radar-Node")

# --- إعدادات الخوارزمية ---
ICEBERG_THRESHOLD = 5.0  # حجم الامتصاص بالـ BTC (يمكنك رفعه لـ 10 لتقليل التنبيهات)

def send_telegram_msg(message):
    """إرسال التنبيهات إلى تليجرام"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ خطأ: إعدادات تليجرام غير مكتملة (Token/Chat ID)")
        return
    
    full_message = f"🤖 **[{INSTANCE_NAME}]**\n{message}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": full_message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ خطأ في إرسال تليجرام: {response.text}")
    except Exception as e:
        print(f"❌ عطل في شبكة التليجرام: {e}")

async def whales_radar():
    """المحرك الأساسي لرصد السيولة"""
    # تهيئة المتغيرات بقيم صفرية لتجنب KeyError
    current_ask_price = 0
    acc_buy_vol = 0
    
    client = await AsyncClient.create()
    bm = BinanceSocketManager(client)
    
    # فتح القنوات (العمق والصفقات)
    ms = bm.multiplex_socket([
        f'{SYMBOL.lower()}@depth10@100ms', 
        f'{SYMBOL.lower()}@trade'
    ])
    
    print(f"📡 {INSTANCE_NAME} بدأ العمل على {SYMBOL}...")
    send_telegram_msg(f"✅ تم تشغيل البوت بنجاح على {SYMBOL}. جاري مراقبة السيولة...")

    try:
        async with ms as mscm:
            while True:
                res = await mscm.recv()
                
                # التحقق من سلامة البيانات المستلمة
                if 'data' not in res or 'stream' not in res:
                    continue
                
                stream = res['stream']
                data = res['data']

                # 1. تحديث سعر البيع (Asks) من سجل الطلبات
                if 'depth' in stream:
                    # التأكد من وجود مفتاح 'a' وعدم فراغه (حل مشكلة KeyError: 'a')
                    if 'a' in data and len(data['a']) > 0:
                        current_ask_price = float(data['a'][0][0])
                    continue

                # 2. مراقبة التنفيذ الفعلي لكشف الامتصاص (Whale Buying)
                elif 'trade' in stream:
                    # لا نبدأ المقارنة إلا إذا استلمنا أول سعر من سجل الطلبات
                    if current_ask_price == 0:
                        continue
                    
                    t_price = float(data.get('p', 0))
                    t_qty = float(data.get('q', 0))
                    is_buyer_maker = data.get('m', False)

                    # إذا كانت صفقة شراء سوقية تمت عند سعر جدار البيع أو أعلى
                    if not is_buyer_maker and t_price >= current_ask_price:
                        acc_buy_vol += t_qty
                        
                        # تحقق من شرط الامتصاص (Iceberg)
                        if acc_buy_vol >= ICEBERG_THRESHOLD:
                            msg = (f"⚠️ **تنبيه حوت (Iceberg Buy)!**\n"
                                   f"🔹 السعر: {t_price}\n"
                                   f"🔹 الكمية الممتصة: {acc_buy_vol:.2f} BTC\n"
                                   f"🔹 الحالة: تجميع/امتصاص سيولة 🚀")
                            send_telegram_msg(msg)
                            acc_buy_vol = 0  # تصفير العداد بعد التنبيه
                    
                    # تصفير العداد إذا تحرك السعر بعيداً (انتهى الامتصاص في هذه المنطقة)
                    if abs(t_price - current_ask_price) > (t_price * 0.001): # فرق 0.1%
                        acc_buy_vol = 0

    except Exception as e:
        print(f"🧨 حدث خطأ مفاجئ: {e}")
        send_telegram_msg(f"🆘 البوت توقف بسبب خطأ: {e}")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    try:
        asyncio.run(whales_radar())
    except KeyboardInterrupt:
        print("🛑 تم إيقاف البوت يدوياً.")
        sys.exit(0)
