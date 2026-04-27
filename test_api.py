import requests

BASE = "http://localhost:8000"
ADDRESS = "0x8ed7af7d0B09B693a81f38947B9Df15c2f008296"

# Test 1: normal chat
print("=== Test 1: normal chat ===")
r = requests.post(f"{BASE}/chat", json={
    "message": f"Check ETH balance for {ADDRESS}",
})
print(f"status: {r.status_code}")
print(f"raw:    {r.text[:300]}")
data = r.json()
print(f"session_id:            {data['session_id']}")
print(f"awaiting_confirmation: {data['awaiting_confirmation']}")
print(f"reply: {data['reply'][:120]}")

# Test 2: confirmation flow
print("\n=== Test 2: confirmation flow ===")
r = requests.post(f"{BASE}/chat", json={
    "message": f"Repay 5 USDC on Aave, my address is {ADDRESS}",
})
data = r.json()
session_id = data["session_id"]
print(f"awaiting_confirmation: {data['awaiting_confirmation']}")
print(f"pending_action: {data['pending_action']}")

print("\n--- confirm yes ---")
r = requests.post(f"{BASE}/confirm", json={
    "session_id": session_id,
    "reply": "yes",
})
data = r.json()
print(f"reply: {data['reply'][:120]}")