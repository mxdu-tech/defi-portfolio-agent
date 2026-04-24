from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from src.agent.nodes import (
    load_session_node,
    agent_node_with_tools,
    save_session_node,
    model
)
from src.agent.state import AgentState
from src.tools import tools

model_with_tools = model.bind_tools(tools)

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "save_session"

def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("load_session", load_session_node)
    workflow.add_node("agent", agent_node_with_tools(model_with_tools))
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("save_session", save_session_node)

    workflow.set_entry_point("load_session")
    workflow.add_edge("load_session", "agent")
    workflow.add_conditional_edges("agent", should_continue,{
        "tools": "tools",
        "save_session": "save_session"
    })
    workflow.add_edge("tools", "agent")
    workflow.add_edge("save_session", END)

    return workflow.compile()

agent = create_graph()
