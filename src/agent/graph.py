from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from src.agent.nodes import (
    confirmation_node,
    execute_node,
    intent_node,
    load_session_node,
    agent_node_with_tools,
    save_session_node,
    model,
    model_fast
)
from src.agent.state import AgentState
from src.tools import tools
from src.agent.nodes import prepare_repay_direct_node

model_with_tools = model.bind_tools(tools)
model_fast_with_tools = model_fast.bind_tools(tools)

PREPARE_TOOLS = {"prepare_repay_tx"}

def route_intent(state: AgentState) -> str:
    if state.get("intent") == "repay":
        return "prepare_repay_direct"
    return "agent_fast" if state.get("intent") == "simple" else "agent"

def route_after_agent(state: AgentState) -> str:
    """Single router for all agent output cases."""
    last = state["messages"][-1]

    # Has tool calls
    if hasattr(last, "tool_calls") and last.tool_calls:
        for tc in last.tool_calls:
            if tc["name"] in PREPARE_TOOLS:
                return "tools_prepare"
        return "tools"

    # No tool calls - check if confirmation is pending
    has_pending = any(
        hasattr(m, "content") and "[PENDING CONFIRMATION]" in m.content for m in state["messages"]
    )
    if has_pending and state.get("pending_action"):
        return "confirmation"
    
    return "save_session"

def route_after_confirmation(state: AgentState) -> str:
    return "execute" if state.get("confirmed") else "save_session"

def create_graph():
    checkpointer = MemorySaver()
    workflow = StateGraph(AgentState)

    workflow.add_node("prepare_repay_direct", prepare_repay_direct_node)
    workflow.add_node("load_session", load_session_node)
    workflow.add_node("classify_intent", intent_node)
    workflow.add_node("agent", agent_node_with_tools(model_with_tools))
    workflow.add_node("agent_fast", agent_node_with_tools(model_fast_with_tools))
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("tools_prepare", ToolNode(tools))
    workflow.add_node("confirmation", confirmation_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("save_session", save_session_node)

    workflow.set_entry_point("load_session")
    workflow.add_edge("load_session", "classify_intent")

    workflow.add_conditional_edges("classify_intent", route_intent, {
        "prepare_repay_direct": "prepare_repay_direct",
        "agent": "agent",
        "agent_fast": "agent_fast",
    })

    # single router for both agent and agent_fast
    for node in ("agent", "agent_fast"):
        workflow.add_conditional_edges(node, route_after_agent, {
            "tools": "tools",
            "tools_prepare": "tools_prepare",
            "confirmation": "confirmation",
            "save_session": "save_session",
        })

    workflow.add_edge("tools", "agent")
    workflow.add_edge("tools_prepare", "agent")

    workflow.add_conditional_edges("confirmation", route_after_confirmation, {
        "execute": "execute",
        "save_session": "save_session",
    })

    workflow.add_edge("execute", "save_session")
    workflow.add_edge("prepare_repay_direct", "save_session")
    workflow.add_edge("save_session", END)

    return workflow.compile(checkpointer=checkpointer)

agent = create_graph()
