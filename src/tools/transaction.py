import os
import json
from langchain_core.tools import tool
from web3 import Web3
from dotenv import load_dotenv
from src.tools.guards import validate_address, validate_repay_amount, is_high_value


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

ERC20_ABI = [
    {
        "name": "approve",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "name": "allowance",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
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
    """Prepare an Aave V3 USDC repay transaction plan for user review.
    Does NOT execute anything. Returns a plan summary and structured action data.
    amount_usdc: amount of USDC to repay
    user_address: wallet address that will sign
    """
    ok, err = validate_address(user_address)
    if not ok:
        return f"Error: {err}"

    ok, err = validate_repay_amount(amount_usdc)
    if not ok:
        return f"Error: {err}"

    warning = ""
    if is_high_value(amount_usdc):
        warning = (
            f"\n HIGH VALUE TRANSACTION: ${amount_usdc:,.2f} USDC. "
            f"Please double-check all details before confirming."
        )

    pool_address = _get_pool_address()
    checksum_user = w3.to_checksum_address(user_address)
    checksum_pool = w3.to_checksum_address(pool_address)
    checksum_usdc = w3.to_checksum_address(USDC_ADDRESS)

    amount_usdc_unit = int(amount_usdc * 1e6)

    pool = w3.eth.contract(
        address=checksum_pool,
        abi=AAVE_POOL_ABI,
    )

    usdc = w3.eth.contract(
        address=checksum_usdc,
        abi=ERC20_ABI,
    )

    # 1. Check current USDC allowance
    allowance = usdc.functions.allowance(
        checksum_user,
        checksum_pool,
    ).call()

    need_approve = allowance < amount_usdc_unit

    # 2. Build approve tx if allowance is insufficient
    approve_tx = None
    if need_approve:
        approve_tx = usdc.functions.approve(
            checksum_pool,
            amount_usdc_unit,
        ).build_transaction({
            "from": checksum_user,
            "gas": 100000,
        })

    # 3. Build repay tx
    repay_tx = pool.functions.repay(
        checksum_usdc,
        amount_usdc_unit,
        2,  # variable debt
        checksum_user,
    ).build_transaction({
        "from": checksum_user,
        "gas": 200000,
    })

    pending_action = {
        "type": "repay",
        "amount_usdc": amount_usdc,
        "user_address": checksum_user,
        "network": network,
        "chain_id": 84532,  # Base Sepolia

        "need_approve": need_approve,

        "approve_tx": {
            "to": checksum_usdc,
            "data": approve_tx["data"],
            "value": "0",
            "gas": approve_tx["gas"],
        } if need_approve else None,

        "repay_tx": {
            "to": checksum_pool,
            "data": repay_tx["data"],
            "value": "0",
            "gas": repay_tx["gas"],
        },

        "asset": checksum_usdc,
        "interest_rate_mode": 2,
        "allowance": allowance,
        "required_allowance": amount_usdc_unit,
    }

    summary = (
        f"Transaction plan ready:{warning}\n"
        f"- Action: Repay {amount_usdc} USDC on Aave V3\n"
        f"- Network: {network}\n"
        f"- Pool: {checksum_pool}\n"
        f"- USDC: {checksum_usdc}\n"
        f"- Approval needed: {need_approve}\n"
        f"- Repay gas limit: {repay_tx['gas']}\n"
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