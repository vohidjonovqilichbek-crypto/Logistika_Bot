import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web
import ccxt

# 1. TOKEN va ADMIN_ID larni Render "Environment Variables" dan o'qiydi
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=TOKEN)
dp = Dispatcher()
exchange = ccxt.binance()

# Kripto va Oltin ro'yxati
crypto_list = [
    'BTC/USDT',   # Bitcoin
    'ETH/USDT',   # Ethereum
    'SOL/USDT',   # Solana
    'PAXG/USDT',  # Oltin (PAX Gold)
    'TON/USDT'    # Toncoin
]

# Webhook kelganda xabarlarni qayta ishlovchi funksiya (Sizning eski kodingiz arxitekturasi)
async def handle(request):
    try:
        token = request.match_info.get('token')
        if token == TOKEN:
            request_body = await request.json()
            update = types.Update(**request_body)
            await dp.feed_update(bot, update)
            return web.Response(text="OK")
    except Exception as e:
        print(f"Webhook xatolik: {e}")
    return web.Response(status=403)

# Narxlarni birjadan olib, chiroyli foizlar bilan matnga aylantiruvchi funksiya
async def get_prices_text():
    try:
        text = "📊 **JORIY BOZOR VA 24h O'ZGARISHLAR** 📊\n"
        text += "-----------------------------------------\n"
        
        for symbol in crypto_list:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            change_percentage = ticker['percentage']
            
            coin_name = symbol.split('/')[0]
            
            if change_percentage >= 0:
                emoji = f"🟢 +{change_percentage:.2f}%"
            else:
                emoji = f"🔴 {change_percentage:.2f}%"
            
            if coin_name == 'PAXG':
                text += f"✨ **GOLD (Oltin)**: `{current_price}` USDT ({emoji})\n"
            else:
                text += f"🔹 **{coin_name}**: `{current_price}` USDT ({emoji})\n"
                
        text += "-----------------------------------------\n"
        text += "🔄 *Ma'lumotlar Binance birjasidan olindi.*"
        return text
    except Exception as e:
        return f"❌ Narxlarni olishda xatolik: {e}"

# Yangilash tugmasini yaratuvchi funksiya
def get_refresh_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="🔄 Narxlarni yangilash", 
        callback_data="refresh_prices"
    ))
    return builder.as_markup()

# ----------------- BOT HANDLERLARI -----------------

# /start komandasi uchun
@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    await message.answer(
        "🚛 **Logistika va Kripto-Bozor botiga xush kelibsiz!**\n\n"
        "📈 Kripto va Oltin narxlarini bilish uchun /narxlar buyrug'ini yuboring.\n"
        "🧮 Shuningdek, menga `0.5 btc` yoki `10 sol` deb yozsangiz, narxini hisoblab beraman!"
    )

# /narxlar komandasi uchun
@dp.message(Command("narxlar"))
async def send_prices(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    prices_text = await get_prices_text()
    await message.answer(prices_text, parse_mode="Markdown", reply_markup=get_refresh_keyboard())

# Tugma bosilganda narxlarni yangilovchi handler
@dp.callback_query(lambda c: c.data == "refresh_prices")
async def refresh_prices_callback(callback_query: types.CallbackQuery):
    await callback_query.answer("Narxlar yangilanmoqda...")
    new_text = await get_prices_text()
    
    if callback_query.message.text != new_text:
        await callback_query.message.edit_text(
            text=new_text,
            parse_mode="Markdown",
            reply_markup=get_refresh_keyboard()
        )

# Matnli xabarlarni o'qib hisoblaydigan kalkulyator (Kripto va Oltin uchun)
@dp.message()
async def crypto_calculator(message: types.Message):
    try:
        parts = message.text.strip().split()
        if len(parts) == 2:
            amount = float(parts[0])
            coin = parts[1].upper()
            
            if coin in ["GOLD", "OLTIN"]:
                coin = "PAXG"
                
            symbol = f"{coin}/USDT"
            
            if symbol in crypto_list:
                await bot.send_chat_action(chat_id=message.chat.id, action="typing")
                ticker = exchange.fetch_ticker(symbol)
                price = ticker['last']
                
                total_usdt = amount * price
                display_name = "GOLD (Oltin)" if coin == "PAXG" else coin
                
                await message.reply(
                    f"🧮 **Kalkulyator natijasi:**\n\n"
                    f"💰 {amount} {display_name} = `{total_usdt:,.2f}` USDT\n\n"
                    f"ℹ️ *1 {display_name} = {price} USDT*",
                    parse_mode="Markdown"
                )
    except ValueError:
        pass
    except Exception as e:
        await message.reply(f"❌ Hisoblashda xatolik: {e}")

# ---------------------------------------------------

# Serverni va botni Webhook orqali ishga tushirish qismi
app = web.Application()
app.router.add_post('/{token}', handle)

if __name__ == '__main__':
    # Render portni muhitdan oladi, u bo'lmasa majburiy 10000 portda ishlaydi
    port = int(os.getenv("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

