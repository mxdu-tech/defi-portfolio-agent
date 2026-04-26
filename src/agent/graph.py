from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from src.agent.nodes import (
    intent_node,
    load_session_node,
    agent_node_with_tools,
    save_session_node,
    model,
    model_fast
)
from src.agent.state import AgentState
from src.tools import tools

model_with_tools = model.bind_tools(tools)
model_fast_with_tools = model_fast.bind_tools(tools)

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "save_session"

def route_intent(state: AgentState):
    return "agent_fast" if state.get("intent") == "simple" else "agent"

def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("load_session", load_session_node)
    workflow.add_node("classify_intent", intent_node)
    workflow.add_node("agent", agent_node_with_tools(model_with_tools))
    workflow.add_node("agent_fast", agent_node_with_tools(model_fast_with_tools))
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("save_session", save_session_node)

    workflow.set_entry_point("load_session")
    workflow.add_edge("load_session", "classify_intent")
    workflow.add_conditional_edges("classify_intent", route_intent, {
        "agent": "agent",
        "agent_fast": "agent_fast"
    })
    workflow.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "save_session": "save_session",
    })
    workflow.add_conditional_edges("agent_fast", should_continue, {
        "tools" : "tools",
        "save_session": "save_session",
    })
    workflow.add_edge("tools", "agent")
    workflow.add_edge("save_session", END)

    return workflow.compile()

agent = create_graph()
