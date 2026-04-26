from langchain_core.tools import tool
from web3 import Web3
from dotenv import load_dotenv
import json
import os

load_dotenv()

network = os.getenv("NETWORK")
rpc_url = os.getenv(f"ALCHEMY_RPC_URL_{network.upper()}")
w3 = Web3(Web3.HTTPProvider(rpc_url))

USDC_ADDRESS = os.getenv("USDC_ADDRESS_BASE_SEPOLIA")

PROVIDER_ABI = [
    {
        "inputs": [],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    }
]

AAVE_POOL_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "asset",            "type": "address"},
            {"internalType": "uint256", "name": "amount",           "type": "uint256"},
            {"internalType": "uint256", "name": "interestRateMode", "type": "uint256"},
            {"internalType": "address", "name": "onBehalfOf",       "type": "address"},
        ],
        "name": "repay",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

def _get_pool_address() -> str:
    provider_address = os.getenv(
        f"AAVE_POOL_ADDRESSES_PROVIDER_{network.upper()}"
    )
    provider = w3.eth.contract(
        address=w3.to_checksum_address(provider_address),
        abi=PROVIDER_ABI,
    )
    return provider.functions.getPool().call()

@tool
def prepare_repay_tx(amount_usdc: float, user_address: str) -> str:
    """Prepare an Aave v3 USDC repay transaction plan for user review.
    Does NOT execute anything. Returns a plan summary and structured action data.
    amount_usdc: amount of USDC to repay
    user_address: wallet address that will sign
    """
    if not w3.is_address(user_address):
        return f"Error: {user_address} is not a valid Ethereum address"
    if amount_usdc <= 0:
        return "Error: amount must be greater than 0"

    pool_address  = _get_pool_address()
    pool          = w3.eth.contract(
        address=w3.to_checksum_address(pool_address),
        abi=AAVE_POOL_ABI,
    )
    amount_usdc_unit    = int(amount_usdc * 1e6)
    checksum_user = w3.to_checksum_address(user_address)

    tx = pool.functions.repay(
        w3.to_checksum_address(USDC_ADDRESS),
        amount_usdc_unit,
        2,
        checksum_user,
    ).build_transaction({
        "from":  checksum_user,
        "nonce": w3.eth.get_transaction_count(checksum_user),
        "gas":   200000,
    })

    # Structured action saved alongside human-readable summary
    pending_action = {
        "type":         "repay",
        "amount_usdc":  amount_usdc,
        "user_address": checksum_user,
        "network":      network,
        "contract":     pool_address,
        "gas":          tx["gas"],
        "nonce":        tx["nonce"],
    }

    summary = (
        f"Transaction plan ready:\n"
        f"- Action:    Repay {amount_usdc} USDC on Aave V3\n"
        f"- Network:   {network}\n"
        f"- Contract:  {pool_address}\n"
        f"- Gas limit: {tx['gas']}\n"
        f"- Nonce:     {tx['nonce']}\n"
        f"[PENDING CONFIRMATION]\n"
        f"[ACTION]{json.dumps(pending_action)}[/ACTION]"
    )
    return summary

def execute_repay(pending_action: dict) -> str:
    """Execute a confirmed repay action from pending_action state.
    Called directly by execute_node — not a LangChain tool.
    """
    # TODO: integrate wallet signing in production
    return (
        f"[DEMO MODE] Transaction broadcast simulated:\n"
        f"- Repaid {pending_action['amount_usdc']} USDC on Aave V3\n"
        f"- Network: {pending_action['network']}\n"
        f"- Status:  success (simulated)\n"
        f"In production this would sign and broadcast via the user's wallet."
    )