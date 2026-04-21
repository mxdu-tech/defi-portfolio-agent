from langchain_openai import ChatOpenAI
from src.agent.state import AgentState
import os
from dotenv import load_dotenv

load_dotenv()

model = ChatOpenAI(
    model="anthropic/claude-sonnet-4-5", 
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def agent_node(state: AgentState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}