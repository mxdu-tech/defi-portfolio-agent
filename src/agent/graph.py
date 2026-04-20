from json import load
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from src.agent.state import AgentState
from dotenv import load_dotenv
import os

load_dotenv()

model = ChatOpenAI(
    model="anthropic/claude-sonnet-4-5", 
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def agent_node(state: AgentState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

def create_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)
    return workflow.compile()

agent = create_graph()