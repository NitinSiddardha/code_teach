from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

# Load env before importing agent
load_dotenv()

from app.agent.teacher_agent import (
    start_session,
    submit_code,
    send_signal,
    end_current_session
)
from app.prompts.parsers import TeacherResponse

app = FastAPI(title="code.teach API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ──────────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    topic: str
    level: str

class SubmitRequest(BaseModel):
    code: str

class SignalRequest(BaseModel):
    signal: str
    detail: Optional[str] = None

# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/api/session/start")
async def start(req: StartRequest):
    try:
        response = start_session(req.topic, req.level)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/submit")
async def submit(req: SubmitRequest):
    try:
        response = submit_code(req.code)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/signal")
async def signal(req: SignalRequest):
    try:
        response = send_signal(req.signal, req.detail)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/end")
async def end():
    try:
        summary = end_current_session()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
