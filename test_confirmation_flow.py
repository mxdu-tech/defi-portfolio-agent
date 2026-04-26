from src.agent.graph import agent
from langgraph.types import Command

SESSION = "test-confirmation"
ADDRESS = "0x8ed7af7d0B09B693a81f38947B9Df15c2f008296"
CONFIG  = {"configurable": {"thread_id": SESSION}}
SEP     = "=" * 50

# ── Flow 1: user confirms ────────────────────────────────────
print(SEP)
print("Flow 1: repay request → confirm yes")

result = agent.invoke(
    {
        "messages": [{"role": "user", "content": f"Repay 5 USDC on Aave, my address is {ADDRESS}"}],
        "session_id": SESSION,
    },
    config=CONFIG,
)
print("Agent:", result["messages"][-1].content)

print(SEP)
print("User: yes")
result = agent.invoke(Command(resume="yes"), config=CONFIG)
print("Agent:", result["messages"][-1].content)

# ── Flow 2: user cancels ─────────────────────────────────────
SESSION2 = "test-confirmation-cancel"
CONFIG2  = {"configurable": {"thread_id": SESSION2}}

print(SEP)
print("Flow 2: repay request → confirm no")

result = agent.invoke(
    {
        "messages": [{"role": "user", "content": f"Repay 5 USDC on Aave, my address is {ADDRESS}"}],
        "session_id": SESSION2,
    },
    config=CONFIG2,
)
print("Agent:", result["messages"][-1].content)

print(SEP)
print("User: no")
result = agent.invoke(Command(resume="no"), config=CONFIG2)
print("Agent:", result["messages"][-1].content)