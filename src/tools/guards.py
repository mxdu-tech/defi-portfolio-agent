from web3 import Web3

# Whitelist of supported assets
SUPPORTED_ASSETS = {"USDC", "USDT", "ETH", "WETH", "WBTC", "AAVE"}

# Transaction limits
MAX_REPAY_USDC = 100_000
MIN_REPAY_USDC = 0.01
HIGH_VALUE_THRESHOLD_USDC = 1_000

def validate_address(address: str) -> tuple[bool, str]:
    if not isinstance(address, str):
        return False, "Address must be a string"
    if not Web3.is_address(address):
        return False, f"Invalid Ethereum address: {address}"
    return True, ""

def validate_repay_amount(amount_usdc: float) -> tuple[bool, str]:
    if amount_usdc < MIN_REPAY_USDC:
        return False, f"Amount too small: minimum is {MIN_REPAY_USDC} USDC"
    if amount_usdc > MAX_REPAY_USDC:
        return False, f"Amount too large: maximum is {MAX_REPAY_USDC} USDC"
    return True, ""

def is_high_value(amount_usdc: float) -> bool:
    return amount_usdc >= HIGH_VALUE_THRESHOLD_USDC

def validate_asset(symbol: str) -> tuple[bool, str]:
    if symbol.upper() not in SUPPORTED_ASSETS:
        supported = ", ".join(sorted(SUPPORTED_ASSETS))
        return False, f"Unsupported asset: {symbol}. Supported: {supported}"
    return True, ""