from src.agent.graph import agent

SESSION = "test-user-001"

# Turn 1: user provides address
print("=== Turn 1: provide address ===")
result = agent.invoke({
    "messages": [{"role": "user", "content": "My wallet is 0x8ed7af7d0B09B693a81f38947B9Df15c2f008296"}],
    "session_id": SESSION,
})
print(result["messages"][-1].content)

# Turn 2: ask without repeating address
print("\n=== Turn 2: ask without address ===")
result = agent.invoke({
    "messages": [{"role": "user", "content": "Check my Aave position"}],
    "session_id": SESSION,
})
print(result["messages"][-1].content)