import redis
import os
from dotenv import load_dotenv
from src.agent.graph import agent
from src.memory.session import (
    get_user_address,
    get_messages,
    get_user_prefs,
    clear_session,
)

load_dotenv()

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

SESSION   = "test-redis-memory"
ADDRESS   = "0x8ed7af7d0B09B693a81f38947B9Df15c2f008296"
SEPARATOR = "─" * 50

def run(session_id: str, content: str) -> str:
    result = agent.invoke({
        "messages": [{"role": "user", "content": content}],
        "session_id": session_id,
    })
    return result["messages"][-1].content

def assert_eq(label: str, actual, expected):
    status = "PASS" if actual == expected else "FAIL"
    print(f"  [{status}] {label}")
    if actual != expected:
        print(f"         expected : {expected}")
        print(f"         actual   : {actual}")

def assert_not_none(label: str, actual):
    status = "PASS" if actual is not None else "FAIL"
    print(f"  [{status}] {label}: {actual}")

def assert_gte(label: str, actual: int, minimum: int):
    status = "PASS" if actual >= minimum else "FAIL"
    print(f"  [{status}] {label}: {actual} (min={minimum})")

# ── Setup ────────────────────────────────────────────────────

print(SEPARATOR)
print("Setup: clearing session")
clear_session(SESSION)
r.delete(f"user:{ADDRESS}:meta")

# ── Test 1: address extraction and session write ─────────────

print(SEPARATOR)
print("Test 1: address extraction + Redis write")
run(SESSION, f"My wallet address is {ADDRESS}")

assert_not_none("address written to session meta", get_user_address(SESSION))
assert_eq("address normalized correctly",
    get_user_address(SESSION),
    "0x8ed7af7d0B09B693a81f38947B9Df15c2f008296"
)

messages = get_messages(SESSION)
assert_gte("messages persisted", len(messages), 1)
assert_not_none("timestamp present on last message", messages[-1].get("ts"))

# ── Test 2: address recall across turns ──────────────────────

print(SEPARATOR)
print("Test 2: address recall — second turn without repeating address")
response = run(SESSION, "Check my Aave position")

has_position_data = any(
    kw in response.lower()
    for kw in ["collateral", "debt", "health factor", "position", "aave"]
)
status = "PASS" if has_position_data else "FAIL"
print(f"  [{status}] agent used remembered address to query Aave")

# ── Test 3: user-level meta persistence ──────────────────────

print(SEPARATOR)
print("Test 3: user-level meta written")
meta = r.hgetall(f"user:{ADDRESS}:meta")
decoded = {k.decode(): v.decode() for k, v in meta.items()}

assert_not_none("first_seen set", decoded.get("first_seen"))
assert_not_none("last_seen set",  decoded.get("last_seen"))

# ── Test 4: session survives multiple turns ───────────────────

print(SEPARATOR)
print("Test 4: session continuity across 3 turns")
run(SESSION, "What is the current gas price?")
run(SESSION, "Is my position healthy?")

messages = get_messages(SESSION)
assert_gte("message count grows across turns", len(messages), 4)

# ── Test 5: clear session preserves user meta ────────────────

print(SEPARATOR)
print("Test 5: clear_session removes session data, keeps user meta")
clear_session(SESSION)

assert_eq("session address cleared", get_user_address(SESSION), None)
assert_eq("session messages cleared", get_messages(SESSION), [])

meta_after = r.hgetall(f"user:{ADDRESS}:meta")
status = "PASS" if meta_after else "FAIL"
print(f"  [{status}] user meta preserved after clear_session")

print(SEPARATOR)
print("Done.")