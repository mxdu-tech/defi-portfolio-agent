from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.state import AgentState
import os
from dotenv import load_dotenv

load_dotenv()

model = ChatOpenAI(
    model="anthropic/claude-sonnet-4-5", 
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def agent_node_with_tools(model_with_tools):
    def node(state: AgentState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = model_with_tools.invoke(messages)
        return {"messages": [response]}
    return node