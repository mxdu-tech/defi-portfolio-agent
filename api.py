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