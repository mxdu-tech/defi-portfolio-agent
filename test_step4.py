from src.agent.graph import agent

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": (
            "Check the ETH balance of this address: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 "
            "and alse tell me if now is a good time to make a transaction."
        )
    }]
})

print("=== Test: Multi-tool in single query ===")
print(result["messages"][-1].content)