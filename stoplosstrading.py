import time
import datetime
import pytz
# import robin_stocks.robinhood as rh
# import tdameritrade as td
import requests
import alpaca_trade_api as tradeapi

# Credentials (use environment variables in production)
# USERNAME = "your_username"
# PASSWORD = "your_password"
# TD_CLIENT_ID = "your_td_client_id"
# TD_ACCOUNT_ID = "your_td_account_id"
# TD_REDIRECT_URI = "your_redirect_uri"
# TD_ACCESS_TOKEN = None

# SCHWAB_CLIENT_ID = "your_schwab_client_id"
# SCHWAB_ACCOUNT_ID = "your_schwab_account_id"
# SCHWAB_REDIRECT_URI = "your_schwab_redirect_uri"
# SCHWAB_ACCESS_TOKEN = None

ALPACA_API_KEY = "PKIVS959YFNIUMVO27Y1"
ALPACA_SECRET_KEY = "2FDF5OXLZPT7unhH6esmuEjaxTsjlAgfxKQM1FDO"
BASE_URL = "https://paper-api.alpaca.markets"

alpaca = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')
# Set U.S. Eastern Time (ET) timezone
eastern = pytz.timezone("America/New_York")

def get_price_alpaca(symbol):
    """Fetch the latest trade price of a symbol from Alpaca."""
    try:
        trade = alpaca.get_latest_trade(symbol)
        return trade.price  # Correct attribute to access price
    except Exception as e:
        print(f"⚠️ Error fetching price: {e}")
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
        time.sleep(60)  # Check every minute

def trade_tqqq_alpaca():
    """Main trading loop for TQQQ."""
    symbol = "TQQQ"

    # If launched outside trading hours, wait until market opens
    wait_for_market_open()

    print("🚀 Market open! Starting trading bot...")

    # Get the first price
    current_price = None
    while current_price is None:
        current_price = get_price_alpaca(symbol)
        if current_price is None:
            print("⚠️ Retrying price fetch...")
            time.sleep(30)

    stop_loss_price = current_price * 0.95  # 5% drop
    sell_price = None

    print(f"✅ Using starting price: {current_price:.2f}")
    print(f"🛑 Stop-loss price set at: {stop_loss_price:.2f}")

    # Trading loop until market closes
    while market_is_open():
        current_price = get_price_alpaca(symbol)
        if current_price is None:
            print("⚠️ Failed to fetch current price, retrying...")
            time.sleep(30)
            continue

        print(f"📊 Current Price: {current_price:.2f}")

        # Sell if price drops to stop-loss
        if sell_price is None and current_price <= stop_loss_price:
            print(f"💰 Selling TQQQ at {current_price:.2f}")
            try:
                alpaca.submit_order(
                    symbol=symbol, qty=1, side='sell', type='market', time_in_force='gtc'
                )
                sell_price = current_price
            except Exception as e:
                print(f"⚠️ Order failed: {e}")

        # Buy back if price rises back to sell price
        elif sell_price and current_price >= sell_price:
            print(f"🛒 Buying back TQQQ at {current_price:.2f}")
            try:
                alpaca.submit_order(
                    symbol=symbol, qty=1, side='buy', type='market', time_in_force='gtc'
                )
                sell_price = None  # Reset sell price after buying back
            except Exception as e:
                print(f"⚠️ Order failed: {e}")

        time.sleep(60)  # Check price every minute

    print("⏳ Market closed. Exiting for today...")
    time.sleep(60 * 60 * 8)  # Sleep 8 hours before next market day
    trade_tqqq_alpaca()  # Restart for the next day

# Start the bot
trade_tqqq_alpaca()