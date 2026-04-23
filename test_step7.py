# scan_aave.py
from src.tools.aave import get_aave_position

# base sepolia testnet
candidates = [
    "0x8ed7af7d0B09B693a81f38947B9Df15c2f008296", 
]

for addr in candidates:
    print(f"\n--- {addr[:10]}... ---")
    print(get_aave_position.invoke({"address": addr}))