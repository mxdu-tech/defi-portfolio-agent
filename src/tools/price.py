import requests
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

SYMBOL_TO_ID = {
    "ETH":  "ethereum",
    "BTC":  "bitcoin",
    "USDC": "usd-coin",
    "USDT": "tether",
    "AAVE": "aave",
    "WBTC": "wrapped-bitcoin",
}

@tool
def get_token_price(symbol: str) -> str:
    """Get the current USD price of a token by its symbol (e.g. ETH, BTC, AAVE)."""
    symbol = symbol.upper().strip()
    coin_id = SYMBOL_TO_ID.get(symbol)

    if not coin_id:
        supported = ", ".join(SYMBOL_TO_ID.keys())
        return f"Unsupported token: {symbol}. Supported: {supported}"

    try:
        response = requests.get(
            COINGECKO_URL,
            params={"ids": coin_id, "vs_currencies": "usd"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        price = data[coin_id]["usd"]
        return f"{symbol} current price: ${price:,.2f} USD"
    except requests.Timeout:
        return f"Price fetch timed out for {symbol}. Try again."
    except Exception as e:
        logger.warning(f"Price fetch failed for {symbol}: {e}")
        return f"Failed to fetch price for {symbol}."