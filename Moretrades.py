import time
import datetime
import pytz
import alpaca_trade_api as tradeapi

# Alpaca API credentials
ALPACA_API_KEY = "your_api_key"
ALPACA_SECRET_KEY = "your_secret_key"
BASE_URL = "https://paper-api.alpaca.markets"

alpaca = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')

# Set U.S. Eastern Time (ET) timezone
eastern = pytz.timezone("America/New_York")

SYMBOLS = ["TQQQ", "SPXL"]  # Trade both TQQQ and SPXL


def get_price(symbol):
    """Fetch the latest trade price of a symbol from Alpaca."""
    try:
        trade = alpaca.get_latest_trade(symbol)
        return trade.price
    except Exception as e:
        print(f"⚠️ Error fetching {symbol} price: {e}")
        return None


def market_is_open():
    """Check if the market is open."""
    try:
        clock = alpaca.get_clock()
        return clock.is_open
    except Exception as e:
        print(f"⚠️ Error checking market status: {e}")
        return False


def wait_for_market_open():
    """Wait until the market opens before proceeding."""
    while not market_is_open():
        print("⏳ Market is closed. Waiting for open...")
        time.sleep(60)


def trade_stocks():
    """Main trading loop for both TQQQ and SPXL."""
    wait_for_market_open()
    print("🚀 Market open! Starting trading bot...")

    stop_loss_prices = {}
    sell_prices = {}
    shares_sold = {}

    # Initialize tracking data for each symbol
    for symbol in SYMBOLS:
        current_price = None
        while current_price is None:
            current_price = get_price(symbol)
            if current_price is None:
                print(f"⚠️ Retrying price fetch for {symbol}...")
                time.sleep(30)
        stop_loss_prices[symbol] = current_price * 0.95  # 5% drop stop-loss
        sell_prices[symbol] = None
        shares_sold[symbol] = 0

        print(f"✅ {symbol} Initial Price: {current_price:.2f}")
        print(f"🛑 {symbol} Stop-loss Price: {stop_loss_prices[symbol]:.2f}")

    while market_is_open():
        current_time = datetime.datetime.now(eastern).time()
        for symbol in SYMBOLS:
            current_price = get_price(symbol)
            if current_price is None:
                print(f"⚠️ Failed to fetch {symbol} price, retrying...")
                time.sleep(30)
                continue

            print(f"📊 {symbol} Current Price: {current_price:.2f}")

            # Sell if price drops to stop-loss
            if sell_prices[symbol] is None and current_price <= stop_loss_prices[symbol]:
                print(f"💰 Selling {symbol} at {current_price:.2f}")
                try:
                    position = alpaca.get_position(symbol)
                    qty = int(position.qty)
                    if qty > 0:
                        alpaca.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='gtc')
                        sell_prices[symbol] = current_price
                        shares_sold[symbol] = qty
                except Exception as e:
                    print(f"⚠️ Sell order failed: {e}")

            # Buy back if price returns to original stop-loss price before 3:30 PM
            if sell_prices[symbol] is not None and current_price >= stop_loss_prices[symbol] and current_time < datetime.time(15, 30):
                print(f"🛒 Buying back {symbol} before 3:30 PM at {current_price:.2f}")
                try:
                    cash_available = sell_prices[symbol] * shares_sold[symbol]
                    qty_to_buy = int(cash_available / current_price)
                    if qty_to_buy > 0:
                        alpaca.submit_order(symbol=symbol, qty=qty_to_buy, side='buy', type='market', time_in_force='gtc')
                        sell_prices[symbol] = None
                        shares_sold[symbol] = 0
                except Exception as e:
                    print(f"⚠️ Buyback order failed: {e}")

            # If stock is bought back before 3:30 PM and falls below stop-loss again, sell it again
            if sell_prices[symbol] is None and current_price <= stop_loss_prices[symbol] and shares_sold[symbol] == 0:
                print(f"💰 Re-selling {symbol} at {current_price:.2f} after buyback")
                try:
                    position = alpaca.get_position(symbol)
                    qty = int(position.qty)
                    if qty > 0:
                        alpaca.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='gtc')
                        sell_prices[symbol] = current_price
                        shares_sold[symbol] = qty
                except Exception as e:
                    print(f"⚠️ Re-sell order failed: {e}")

            # 3:30 PM Buyback using proceeds from sold shares
            if datetime.time(15, 30) <= current_time <= datetime.time(15, 31) and shares_sold[symbol] > 0:
                print(f"🛒 Buying back {symbol} with all proceeds at {current_price:.2f}")
                try:
                    cash_available = sell_prices[symbol] * shares_sold[symbol]
                    qty_to_buy = int(cash_available / current_price)
                    if qty_to_buy > 0:
                        alpaca.submit_order(symbol=symbol, qty=qty_to_buy, side='buy', type='market', time_in_force='gtc')
                        sell_prices[symbol] = None
                        shares_sold[symbol] = 0
                except Exception as e:
                    print(f"⚠️ Buyback order failed: {e}")

        time.sleep(60)  # Check prices every minute

    print("⏳ Market closed. Restarting tomorrow...")
    time.sleep(60 * 60 * 8)  # Sleep 8 hours before the next market day
    trade_stocks()  # Restart for the next day


# Start the bot
trade_stocks()
