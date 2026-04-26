from src.tools.chain import get_eth_balance, get_gas_price
from src.tools.aave import get_aave_position, analyze_aave_risk
from src.tools.price import get_token_price
from src.tools.transaction import prepare_repay_tx

tools = [get_eth_balance, get_gas_price, get_aave_position, analyze_aave_risk, get_token_price, prepare_repay_tx]