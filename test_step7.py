from src.agent.graph import agent

result = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": (
                "Check my Aave position for 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 "
                "and tell me if I need to take any action to protect it."
            )
        }
    ]
})

print("=== Test: Aave position + risk analysis ===")
print(result["messages"][-1].content)