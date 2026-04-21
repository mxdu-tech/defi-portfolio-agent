from langchain_core.tools import tool
from web3 import Web3
from dotenv import load_dotenv
import os

import web3

load_dotenv()

network = os.getenv("NETWORK")
rpc_url = os.getenv(f"ALCHEMY_RPC_URL_{network.upper()}")
w3 = Web3(web3.HTTPProvider(rpc_url))

@tool
def get_eth_balance(address: str) -> str:
    """Get the ETH balance of an Ethereum address"""
    if not w3.is_address(address):
        return f"error: {address} is not a valid Ethereum address."

    checksum_address = w3.to_checksum_address(address)
    balance_wei = w3.eth.get_balance(checksum_address)
    balance_eth = w3.from_wei(balance_wei, "ether")

    return f"Address {address[:6]}...{address[-4:]}, balance: {float(balance_eth):.4f} ETH"

@tool
def get_gas_price() -> str:
    """Get the current gas price on the Ethereum network"""
    gas_wei = w3.eth.gas_price
    gas_gwei = w3.from_wei(gas_wei, "gwei")

    if gas_gwei < 20:
        advice = "Gas is low, good time to send transactions."
    elif gas_gwei < 50:
        advice = "Gas is moderate"
    else:
        advice = "Gas is high, consider waiting"
    
    return f"Current gas price: {float(gas_gwei): .2f} Gwei. {advice}"