from langchain_core.callbacks import RetrieverManagerMixin
from langchain_core.tools import tool
from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()

UINT256_MAX = 2**256 - 1

network = os.getenv("NETWORK")
rpc_url = os.getenv(f"ALCHEMY_RPC_URL_{network.upper()}")
w3 = Web3(Web3.HTTPProvider(rpc_url))

AAVE_POOL_ADDRESS = os.getenv(f"AAVE_POOL_{network.upper()}")

AAVE_POOL_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"internalType": "uint256", "name": "totalCollateralBase", "type": "uint256"},
            {"internalType": "uint256", "name": "totalDebtBase", "type": "uint256"},
            {"internalType": "uint256", "name": "availableBorrowBase", "type": "uint256"},
            {"internalType": "uint256", "name": "currentLiquidationThresold", "type": "uint256"},
            {"internalType": "uint256", "name": "ltv", "type": "uint256"},
            {"internalType": "uint256", "name": "healthFactor", "type": "uint256"},
        ],
        "stateMutablity": "view",
        "type": "function"
    }
]

def _get_health_status(health_factor: float) -> str:
    if health_factor == 0:
        return "no active position"
    elif health_factor < 1.0:
        return "CRITICAL - at risk of liquidation"
    elif health_factor < 1.2:
        return "DANGER - very close to liquidation"
    elif health_factor < 1.5:
        return "WARNING - monitor closely"
    else:
        return "HEALTHY"

@tool
def get_aave_position(address: str) -> str:
    """Query an address Aave V3 lending position including collateral, debt, and health factor."""
    if not w3.is_address(address):
        return f"Error: {address} is not a valid Ethereum address."
    
    chechsum_address = w3.to_checksum_address(address)
    pool = w3.eth.contract(
        address=w3.to_checksum_address(AAVE_POOL_ADDRESS),
        abi=AAVE_POOL_ABI
    )

    data = pool.functions.getUserAccountData(chechsum_address).call()

    total_collateral_usd = data[0] / 1e8
    total_debt_usd = data[1] / 1e8
    available_borrows = data[2] / 1e8
    health_factor_raw = data[5]

    if total_collateral_usd == 0:
        return f"Address {address[:6]}...{address[-4:]} has no active Aave V3 position on {network}."
    
    if health_factor_raw == UINT256_MAX:
        health_factor_display = "No debt (infinite)"
        status = "HEALTHY"
    else:
        health_factor = health_factor_raw / 1e18
        health_factor_display = f"{health_factor: 4f}"
        status = _get_health_status(health_factor_raw)

    return f"""Aave V3 Position ({network}) for {address[:6]}...{address[-4:]}:
            - Total Collateral: ${total_collateral_usd:.2f} USD
            - Total Debt:       ${total_debt_usd:.2f} USD
            - Available to Borrow: ${available_borrows:.2f} USD
            - Health Factor:    {health_factor_display} ({status})"""


@tool
def analyze_aave_risk(
    total_collateral_usd: float,
    total_debt_usd: float,
    health_factor: float
) -> str:
    """Analyze Aave position risk and provide actionable recommendations.
    Use this after get_aave_position to give the user specific advice.
    """
    if total_debt_usd == 0:
        return "No debt detected. Position is safe with no liquidation risk."
    
    target_hf = 1.8
    liquidation_thresold = 0.825

    required_collateral = (target_hf * total_collateral_usd) / liquidation_thresold
    collateral_to_add = max(0, required_collateral - total_collateral_usd)

    max_debt_for_target = (total_collateral_usd * liquidation_thresold) / target_hf
    debt_to_repay = max(0, total_debt_usd - max_debt_for_target)

    status = _get_health_status(health_factor)

    return f"""Risk Analysis:
        - Status: {status}
        - To reach Health Factor {target_hf}:
        Option A: Add ${collateral_to_add:.2f} USD worth of collateral
        Option B: Repay ${debt_to_repay:.2f} USD worth of debt
        - Current ratio: ${total_debt_usd:.2f} debt against ${total_collateral_usd:.2f} collateral"""