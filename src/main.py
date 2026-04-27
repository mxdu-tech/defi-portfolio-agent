import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.types import Command
from langgraph.errors import GraphInterrupt
from langchain_core.messages import AIMessage as LCAIMessage
from src.agent.graph import agent
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DeFi Portfolio Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ────────────────────────────────

class ChatRequest(BaseModel):
    message:    str
    session_id: Optional[str] = None

class ConfirmRequest(BaseModel):
    session_id: str
    reply:      str   # "yes" or "no"

class ChatResponse(BaseModel):
    session_id:            str
    reply:                 str
    awaiting_confirmation: bool
    pending_action:        Optional[dict] = None

# ── Helpers ──────────────────────────────────────────────────

def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}

def _is_interrupted(result: dict) -> bool:
    """Check if graph paused at a confirmation node."""
    last = result["messages"][-1]
    return (
        hasattr(last, "content")
        and "[PENDING CONFIRMATION]" in last.content
    )

def _build_response(result: dict, session_id: str) -> ChatResponse:
    import re

    messages = result.get("messages", [])

    # Last plain-text AI message (no tool_calls)
    last_msg = None
    for m in reversed(messages):
        if isinstance(m, LCAIMessage):
            if not (hasattr(m, "tool_calls") and m.tool_calls):
                last_msg = m.content
                break

    if not last_msg:
        last_msg = messages[-1].content if messages else ""

    # Strip internal tags
    last_msg = re.sub(r"\[ACTION\].*?\[/ACTION\]", "", last_msg, flags=re.DOTALL)
    last_msg = last_msg.replace("[PENDING CONFIRMATION]", "").strip()

    # awaiting_confirmation = pending_action exists and not yet confirmed
    pending       = result.get("pending_action")
    awaiting      = pending is not None

    return ChatResponse(
        session_id=session_id,
        reply=last_msg,
        awaiting_confirmation=awaiting,
        pending_action=pending,
    )

# ── Routes ───────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    config     = _config(session_id)

    try:
        result = agent.invoke(
            {
                "messages":   [{"role": "user", "content": req.message}],
                "session_id": session_id,
            },
            config=config,
        )
        logger.info(f"result type: {type(result)}")
        logger.info(f"result keys: {result.keys() if result else 'None'}")
        logger.info(f"last message: {result['messages'][-1] if result else 'None'}")
        return _build_response(result, session_id)

    except GraphInterrupt as e:
        # Graph paused at confirmation_node — extract interrupt payload
        payload = e.args[0] if e.args else {}
        plan    = ""
        action  = None

        if isinstance(payload, (list, tuple)) and len(payload) > 0:
            interrupt_value = payload[0].value if hasattr(payload[0], "value") else {}
            plan   = interrupt_value.get("plan", "")
            action = interrupt_value.get("action")

        return ChatResponse(
            session_id=session_id,
            reply=(
                f"{plan}\n\n"
                f"Please confirm: type **yes** to execute or **no** to cancel."
            ),
            awaiting_confirmation=True,
            pending_action=action,
        )

    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/confirm", response_model=ChatResponse)
async def confirm(req: ConfirmRequest):
    config = _config(req.session_id)

    try:
        result = agent.invoke(
            Command(resume=req.reply),
            config=config,
        )
        return _build_response(result, req.session_id)

    except GraphInterrupt as e:
        # Should not happen after confirm, but handle gracefully
        return ChatResponse(
            session_id=req.session_id,
            reply="Unexpected interruption after confirmation.",
            awaiting_confirmation=True,
        )

    except Exception as e:
        logger.exception("Confirm error")
        raise HTTPException(status_code=500, detail=str(e))