import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from . import agent
from .tools import knowledge

app = FastAPI(title="ArchDesign Agent")
FRONT = Path(__file__).resolve().parents[1] / "frontend"
if not FRONT.exists():
    FRONT = Path(__file__).resolve().parents[2] / "frontend"


class Msg(BaseModel):
    role: str
    content: str

class ChatIn(BaseModel):
    messages: list[Msg]
    country: str = "TH"


@app.post("/api/chat")
def chat(body: ChatIn):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(400, "ANTHROPIC_API_KEY is not set (see .env.example)")
    reply, trace = agent.run([m.model_dump() for m in body.messages], body.country)
    return {"reply": reply, "tools": trace}


@app.get("/api/knowledge")
def kb_list():
    return knowledge.list_files()

@app.post("/api/knowledge")
async def kb_upload(category: str = Form(...), file: UploadFile = File(...)):
    try:
        return {"saved": knowledge.save(category, file.filename, await file.read())}
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.delete("/api/knowledge/{category}/{name}")
def kb_delete(category: str, name: str):
    knowledge.delete(category, name)
    return {"deleted": name}

@app.get("/api/health")
def health():
    return {"ok": True, "gpu": os.environ.get("GPU_ENABLED") == "1"}


@app.get("/")
def index():
    return FileResponse(FRONT / "index.html")
