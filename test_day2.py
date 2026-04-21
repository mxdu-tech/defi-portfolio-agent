from src.agent.graph import agent

result = agent.invoke({
    "messages": [{"role": "user", "content": "Hello, what can you do?"}]
})
print("=== Test 1: Normal Conversation ===")
print(result["messages"][-1].content)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Check the ETH balance of this address: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    }]
})

print("\n=== Test 2: Tool Invocation ===")
print(result["messages"][-1].content)