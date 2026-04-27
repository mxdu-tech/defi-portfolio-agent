import os
import re
import json
import logging
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.state import AgentState
from src.memory import session
from src.memory.session import (
    get_user_address, 
    save_message,
    save_session_address,
    save_user_meta
)
from src.tools.transaction import execute_repay

logger = logging.getLogger(__name__)
audit = logging.getLogger("audit")

EVM_ADDRESS_RE = re.compile(r"0x[a-fA-F0-9]{40}")
ACTION_RE       = re.compile(r"\[ACTION\](.*?)\[/ACTION\]", re.DOTALL)
PREPARE_TOOLS   = {"prepare_repay_tx"}


model = ChatOpenAI(
    model="anthropic/claude-sonnet-4-5", 
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

SIMPLE_INTENTS = {
    "greeting", "help", "balance", "gas", "price"
}

SIMPLE_INTENT_RE = re.compile(
    r"\b(hi|hello|help|what can you do"
    r"|gas price|eth price|btc price|token price"
    r"|check balance|eth balance)\b",
    re.IGNORECASE,
)

model_fast = ChatOpenAI(
    model="deepseek/deepseek-chat",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def load_session_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "default")
    stored_address = get_user_address(session_id)
    return{
        "user_address": stored_address or state.get("user_address")
    }

def agent_node_with_tools(model_with_tools):
    def node(state: AgentState):
        messages = state["messages"]

        # Build system prompt - inject known address if available
        system_content = SYSTEM_PROMPT
        if state.get("user_address"):
            system_content += (
                f"\n\nThe user's wallet address is: {state['user_address']}"
            )

        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=system_content)] + messages
        else:
            messages[0] = SystemMessage(content=system_content)
        
        response = model_with_tools.invoke(messages)

        # Extract address from latest human message if not already in state
        new_address = state.get("user_address")
        if not new_address:
            last_human = next(
                (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
            )
            if last_human:
                match = EVM_ADDRESS_RE.search(last_human.content)
                if match:
                    new_address = match.group(0)

        
        pending_action = state.get("pending_action")
        if not pending_action:
            for m in reversed(state["messages"]):
                if hasattr(m, "content"):
                    action_match = ACTION_RE.search(m.content)
                    if action_match:
                        try:
                            pending_action = json.loads(action_match.group(1))
                        except json.JSONDecodeError:
                            pass
                        break

        return {
            "messages":      [response],
            "user_address":  new_address,
            "pending_action": pending_action,
        }

    return node


def save_session_node(state: AgentState) -> dict:
    """Write phase: persist state to Redis after reasoning completes."""
    session_id = state.get("session_id", "default")
    messages = state["messages"]
    address = state.get("user_address")

    # persist last human and AI messages
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    last_ai = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage)), None
    )
    if last_human:
        save_message(session_id, "user", last_human.content)
    if last_ai:
        save_message(session_id, "assistant", last_ai.content)
    
    # persist address at both session and user level
    if address:
        save_session_address(session_id, address) # session level
        save_user_meta(address)

    # Audit log - only fires when execute_node actually ran
    executed = state.get("executed_action")
    if executed:
        audit.info(
            "TRANSACTION_EXECUTED session=%s address=%s action=%s",
            session_id,
            address,
            executed
        )
    
    return {"executed_action": None}


def intent_node(state: AgentState) -> dict:
    last_human = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        None,
    )
    if not last_human:
        return {"intent": "complex"}

    text = last_human.content.lower()

    # DeepSeek only handles pure conversation — no tools involved
    is_simple = (
        len(text.split()) <= 8
        and SIMPLE_INTENT_RE.search(text) is not None
        and not any(kw in text for kw in [
            "aave", "health factor", "liquidat", "repay",
            "borrow", "collateral", "position", "analyze",
            "balance", "address", "0x", "gas", "price",
            "eth", "btc", "usdc", "token",
        ])
    )
    return {"intent": "simple" if is_simple else "complex"}


def confirmation_node(state: AgentState) -> dict:
    """Interrupt and wait for user yes/no on a pending transaction."""
    logger.info("confirmation_node reached — calling interrupt()")

    pending = state.get("pending_action", {})

    plan_msg = next(
        (m for m in reversed(state["messages"])
        if hasattr(m, "content") and "[PENDING CONFIRMATION]" in m.content),
        None
    )

    plan_text = ""
    if plan_msg:
        plan_text = ACTION_RE.sub("", plan_msg.content)
        plan_text = plan_text.replace("[PENDING CONFIRMATION]", "").strip()
    
    logger.info(f"interrupting with plan: {plan_text[:80]}")
    
    user_reply = interrupt({
        "plan": plan_text,
        "action": pending,
        "prompt": "Type 'yes' to confirm or 'no' to cancel."
    })

    logger.info(f"interrupt resumed with: {user_reply!r}")

    confirmed = isinstance(user_reply, str) and user_reply.strip().lower() in {"yes", "y"}

    if confirmed is True:
        return {"confirmed": confirmed}
    else:
        return {
            "confirmed": False,
            "pending_action": None,
            "messages": [AIMessage(content="Transaction cancelled. No action was executed.")]
        }


def execute_node(state: AgentState) -> dict:
    """Execute confirmed transaction using pending_action from state."""

    pending = state.get("pending_action")
    if not pending:
        return {"messages": AIMessage(content="Error: no pending action found.")}
    
    action_type = pending.get("type")

    if action_type == "repay":
        result = execute_repay(pending)
    else:
        result = f"Unknown action type: {action_type}"
    
    return {
        "messages": [AIMessage(content=result)],
        "pending_action": None,
        "confirmed": None,
        "executed_action": pending
    }