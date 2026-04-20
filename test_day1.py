from src.agent.graph import agent

result = agent.invoke({
    "messages": [{"role": "user", "content": "你好，请用一句话介绍你自己。"}]
})

print(result["messages"][-1].content)

