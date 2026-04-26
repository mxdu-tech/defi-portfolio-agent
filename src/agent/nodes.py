import os
import re
import logging
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.state import AgentState
from src.memory.session import (
    get_user_address, 
    save_message,
    save_session_address,
    save_user_meta
)

logger = logging.getLogger(__name__)

EVM_ADDRESS_RE = re.compile(r"0x[a-fA-F0-9]{40}")


model = ChatOpenAI(
    model="anthropic/claude-sonnet-4-5", 
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
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
        
        return {
            "messages": [response],
            "user_address": new_address
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
    
    return {}

SIMPLE_INTENTS = {
    "greeting", "help", "balance", "gas", "price"
}

SIMPLE_INTENT_RE = re.compile(
    r"\b(hi|hello|help|what can you do"
    r"|gas price|eth price|btc price|token price"
    r"|check balance|eth balance)\b",
    re.IGNORECASE,
)

def intent_node(state: AgentState) -> dict:
    """Classify intent complexity to route to the appropriate model."""
    last_human = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        None,
    )
    if not last_human:
        return {"intent": "complex"}

    text = last_human.content.lower()

    # Simple: short message with no DeFi analysis keywords
    is_simple = (
        len(text.split()) <= 10
        and SIMPLE_INTENT_RE.search(text) is not None
        and not any(kw in text for kw in [
            "aave", "health factor", "liquidat", "repay",
            "borrow", "collateral", "position", "analyze"
        ])
    )

    return {"intent": "simple" if is_simple else "complex"}