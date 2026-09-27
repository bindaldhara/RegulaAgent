from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agent, auth, eval, health, voice

_root_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_root_env)

app = FastAPI(title="RegulaAgent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(voice.router, prefix="/api/v1")
app.include_router(eval.router, prefix="/api/v1")
