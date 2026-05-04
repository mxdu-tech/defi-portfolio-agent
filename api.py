from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.agent.graph import agent

app = FastAPI(title="DeFi Portfolio Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://defi-agent-frontend.vercel.app",
        "https://defi-agent.mxdu.me",
        "https://portfolio-agent.defi.mxdu.me",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str

class ConfirmRequest(BaseModel):
    session_id: str = "default"
    reply: str = "yes"
    tx_hash: str | None = None

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = agent.invoke(
        {
            "messages": [{"role": "user", "content": req.message}],
            "session_id": req.session_id,
        },
        config={
            "configurable": {
                "thread_id": req.session_id,
            }
        },
    )

    return {
        "response": result["messages"][-1].content
    }

@app.post("/confirm", response_model=ChatResponse)
def confirm(req: ConfirmRequest):
    if req.reply != "yes":
        return {"response": "Transaction cancelled."}

    if not req.tx_hash:
        return {"response": "Transaction was not submitted. No transaction hash received."}

    explorer_url = f"https://sepolia.basescan.org/tx/{req.tx_hash}"

    return {
        "response": (
            "Transaction submitted successfully.\n\n"
            f"Transaction hash:\n{req.tx_hash}\n\n"
            f"View on Base Sepolia explorer:\n{explorer_url}\n\n"
            "You can also ask me to check your updated Aave position."
        )
    }