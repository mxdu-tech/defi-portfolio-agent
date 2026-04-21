from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from src.agent.nodes import model, agent_node_with_tools
from src.agent.state import AgentState
from src.tools import tools

model_with_tools = model.bind_tools(tools)

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

def create_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node_with_tools(model_with_tools))
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")

    return workflow.compile()

agent = create_graph()
