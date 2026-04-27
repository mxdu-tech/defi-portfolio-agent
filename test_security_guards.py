from src.tools.guards import validate_address, validate_repay_amount, is_high_value
from src.tools.transaction import prepare_repay_tx

SEP = "─" * 50

print(SEP)
print("Test 1: address validation")
cases = [
    ("0x8ed7af7d0B09B693a81f38947B9Df15c2f008296", True),
    ("0xinvalid",                                   False),
    ("not-an-address",                              False),
    ("",                                            False),
]
for addr, expected in cases:
    ok, err = validate_address(addr)
    status = "PASS" if ok == expected else "FAIL"
    print(f"  [{status}] {addr[:20]!r:22} → valid={ok} {err}")

print(SEP)
print("Test 2: amount validation")
cases = [
    (5.0,      True),
    (0.001,    False),   # below min
    (200_000,  False),   # above max
    (1_500,    True),    # high value but valid
]
for amount, expected in cases:
    ok, err = validate_repay_amount(amount)
    status = "PASS" if ok == expected else "FAIL"
    print(f"  [{status}] amount={amount:<10} → valid={ok} {err}")

print(SEP)
print("Test 3: high value threshold")
for amount in [999, 1000, 1001]:
    hi = is_high_value(amount)
    print(f"  amount={amount} → high_value={hi}")

print(SEP)
print("Test 4: guard rejects invalid input to prepare_repay_tx")
print(prepare_repay_tx.invoke({"amount_usdc": -1,    "user_address": "0x8ed7af7d0B09B693a81f38947B9Df15c2f008296"}))
print(prepare_repay_tx.invoke({"amount_usdc": 5.0,   "user_address": "0xinvalid"}))
print(prepare_repay_tx.invoke({"amount_usdc": 999999, "user_address": "0x8ed7af7d0B09B693a81f38947B9Df15c2f008296"}))