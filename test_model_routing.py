from src.agent.graph import agent

SESSION = "test-routing"

cases = [
    ("simple",  "What is the ETH price?"),
    ("simple",  "Hi, what can you do?"),
    ("complex", "Analyze my Aave position for 0x8ed7af7d0B09B693a81f38947B9Df15c2f008296 and tell me if I'm at risk of liquidation"),
    ("complex", "What should I repay to bring my health factor above 1.8?"),
]

for expected_intent, message in cases:
    result = agent.invoke({
        "messages": [{"role": "user", "content": message}],
        "session_id": SESSION,
    })
    actual_intent = result.get("intent", "unknown")
    status = "PASS" if actual_intent == expected_intent else "FAIL"
    print(f"[{status}] intent={actual_intent} | {message[:60]}")