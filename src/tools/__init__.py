from langchain_core.tools import tool

@tool
def get_eth_balance(address: str) -> str:
    """Retrieve the ETH balance of a given Ethereum address."""
    return f"[Placeholder] ETH balance lookup for address {address} will be implemented in the future"

tools = [get_eth_balance]