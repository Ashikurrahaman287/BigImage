import os
import random
import io
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import MessageHandler, filters

# ---------------- Bybit API ----------------
def get_bybit_price(symbol="BTCUSDT"):
    url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}"
    r = requests.get(url).json()
    price = float(r["result"]["list"][0]["lastPrice"])
    change = float(r["result"]["list"][0]["price24hPcnt"]) * 100
    return price, change

def get_coin_ranking(symbol="BTCUSDT"):
    url = "https://api.bybit.com/v5/market/tickers?category=spot"
    r = requests.get(url).json()
    coins = r["result"]["list"]
    # Sort by 24h volume descending
    coins_sorted = sorted(coins, key=lambda x: float(x["turnover24h"]), reverse=True)
    for idx, c in enumerate(coins_sorted, start=1):
        if c["symbol"] == symbol:
            return idx
    return None


import random
from PIL import ImageDraw


def draw_random_background_chart(img, price_change):
    """
    Draws a random mini chart in the background
    price_change: float, to decide chart color (green/red)
    """
    draw = ImageDraw.Draw(img)
    w, h = img.size
    num_points = 50
    # Generate random points
    prices = [random.uniform(0.4, 0.6) for _ in range(num_points)]

    # smooth random variation
    for i in range(1, num_points):
        prices[i] = max(0, min(1, prices[i - 1] + random.uniform(-0.05, 0.05)))

    # convert to pixel coordinates
    points = [(i * w / (num_points - 1), h * (1 - p)) for i, p in enumerate(prices)]

    # choose color based on price change
    color = (0, 255, 0) if price_change >= 0 else (255, 0, 0)

    # draw the line
    draw.line(points, fill=color, width=2)




def format_price(price):
    if price >= 1:
        return f"${price:,.2f}"       # normal coins $123.45
    elif price >= 0.01:
        return f"${price:,.4f}"       # small coins $0.1234
    elif price >= 0.0001:
        return f"${price:,.6f}"       # tiny coins $0.000123
    else:
        return f"${price:.8f}"        # very tiny coins $0.00000012




# ---------------- Dark Theme Colors ----------------
DARK_COLORS = [
    (18,18,18), (30,30,30), (40,40,40), (45,45,60),
    (25,25,112), (34,34,34), (50,50,50),
]

# ---------------- Price Card Generator ----------------
def make_price_card_clean(symbol, price, change):
    # Background
    bg_color = random.choice(DARK_COLORS)
    img = Image.new("RGB", (600, 300), color=bg_color)

    # Draw random chart in background
    draw_random_background_chart(img, change)

    draw = ImageDraw.Draw(img)

    # Fonts
    try:
        font_big = ImageFont.truetype("arialbd.ttf", 60)
        font_small = ImageFont.truetype("arialbd.ttf", 30)
        font_medium = ImageFont.truetype("arialbd.ttf", 24)
        font_brand = ImageFont.truetype("arialbd.ttf", 18)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_brand = ImageFont.load_default()

    # Coin info
    symbol_full = symbol.upper()
    symbol_for_rank = symbol_full if symbol_full.endswith("USDT") else symbol_full + "USDT"
    ranking = get_coin_ranking(symbol_for_rank)
    rank_text = f"#{ranking}" if ranking else ""

    # Left top: coin + rank
    draw.text((30, 30), symbol_full, font=font_small, fill="white")
    draw.text((30, 70), rank_text, font=font_medium, fill="white")

    # Top right: 24h change
    change_text = f"{change:+.2f}%"
    try:
        draw.text((570, 30), change_text, font=font_small, fill="lime" if change>=0 else "red", anchor="ra")
        draw.text((570, 70), "24 hours", font=font_medium, fill="white", anchor="ra")
    except TypeError:
        draw.text((470, 30), change_text, font=font_small, fill="lime" if change>=0 else "red")
        draw.text((470, 70), "24 hours", font=font_medium, fill="white")

    # Center price
    try:
        draw.text((300, 150), format_price(price), font=font_big, fill="white", anchor="mm")
    except TypeError:
        draw.text((180, 150), format_price(price), font=font_big, fill="white")

    # Bottom: branding + date
    width, height = img.size
    website_text = "www.BigONE.com"
    date_text = datetime.utcnow().strftime("%d %b %Y")
    try:
        draw.text((10, height-30), website_text, font=font_brand, fill="white", anchor="ls")
        draw.text((590, height-30), date_text, font=font_brand, fill="white", anchor="rs")
    except TypeError:
        draw.text((10, height-30), website_text, font=font_brand, fill="white")
        draw.text((400, height-30), date_text, font=font_brand, fill="white")

    # Save to buffer
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf



async def message_coin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper().replace("?", "")  # remove ? and make uppercase
    if text in COIN_MAP:
        symbol = COIN_MAP[text]
    else:
        symbol = text + "USDT"

    try:
        price, change = get_bybit_price(symbol)
        image_buf = make_price_card_clean(text, price, change)
        await update.message.reply_photo(photo=image_buf)
        image_buf.close()
    except Exception as e:
        # optionally ignore or send error
        pass



# ---------------- Command Handlers ----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to BigONE Crypto Bot!\n\n"
        "Use /P <coin> to get the latest price card.\n"
        "Example: /P BTC"
    )

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) == 0:
            await update.message.reply_text("Usage: /P BTC")
            return

        coin = context.args[0].upper()
        price, change = get_bybit_price(coin + "USDT")
        image_buf = make_price_card_clean(coin, price, change)

        await update.message.reply_photo(photo=image_buf)
        image_buf.close()
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


COIN_MAP = {
    "BTC": "BTCUSDT",
    "BITCOIN": "BTCUSDT",
    "ETH": "ETHUSDT",
    "ETHEREUM": "ETHUSDT",
    "SHIB": "SHIBUSDT",
    "PEPE": "PEPEUSDT",
}




# ---------------- Main ----------------
def main():
    TOKEN = "8020806889:AAFMjoorhhPbr2Z60Qg6EuKDIfjfJHZk-hw"
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("P", price_command))
    # Message handler for coin names (Btc, btc?, etc.)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_coin_handler))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
