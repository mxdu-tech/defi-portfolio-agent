from src.tools.aave import get_aave_position

# Test 1: address with no position
print("=== Test 1: No position ===")
print(get_aave_position.invoke({"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}))

# Test 2: invalid address
print("\n=== Test 2: Invalid address ===")
print(get_aave_position.invoke({"address": "0xinvalid"}))