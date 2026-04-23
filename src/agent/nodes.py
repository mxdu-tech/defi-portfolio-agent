from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.state import AgentState
import os
from dotenv import load_dotenv

from src.memory.session import get_user_address, save_message, save_user_address

load_dotenv()

model = ChatOpenAI(
    model="anthropic/claude-sonnet-4-5", 
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def agent_node_with_tools(model_with_tools):
    def node(state: AgentState):
        session_id = state.get("session_id", "default")
        messages = state["messages"]

        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        # Inject remembered address into system prompt if available
        saved_address = get_user_address(session_id)
        if saved_address and state.get("user_address") is None:
            address_hint = f"\n\nThe user's wallet address if: {saved_address}"
            messages[0] = SystemMessage(content=SYSTEM_PROMPT + address_hint)
        
        response = model_with_tools.invoke(messages)

        # Persist last user message and response
        last_human = next(
            (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
        )
        if last_human:
            save_message(session_id, "user", last_human.content)
        save_message(session_id, "assistant", response.content)

        return {"messages": [response]}
    return node