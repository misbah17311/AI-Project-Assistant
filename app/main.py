from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.routers import projects, conversations, images, memory, agents

app = FastAPI(
    title="AI Project Assistant",
    description="Chat with Claude, generate images, and organize project knowledge",
    version="1.0.0",
)

# allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount all routers
app.include_router(projects.router)
app.include_router(conversations.router)
app.include_router(images.router)
app.include_router(memory.router)
app.include_router(agents.router)


@app.get("/")
def serve_frontend():
    return FileResponse(Path(__file__).resolve().parent.parent / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "running", "service": "ai-project-assistant"}
