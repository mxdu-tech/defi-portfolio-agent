from optparse import Option
from typing import Annotated, Optional
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_address: Optional[str]
    pending_action: Optional[str]
    session_id: Optional[str]