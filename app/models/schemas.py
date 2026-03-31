from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Projects ──

class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    goals: Optional[str] = None
    target_audience: Optional[str] = None
    brand_guidelines: Optional[str] = None
    reference_links: Optional[list[str]] = Field(default_factory=list)

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    goals: Optional[str] = None
    target_audience: Optional[str] = None
    brand_guidelines: Optional[str] = None
    reference_links: Optional[list[str]] = None

class ProjectOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    goals: Optional[str] = None
    target_audience: Optional[str] = None
    brand_guidelines: Optional[str] = None
    reference_links: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


# ── Conversations ──

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Chat"

class ConversationOut(BaseModel):
    id: str
    project_id: str
    title: Optional[str] = None
    created_at: str


# ── Messages ──

class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str  # user, assistant, tool
    content: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    tool_results: Optional[list[dict]] = None
    created_at: str


# ── Chat ──

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str
    tool_calls_made: list[dict] = Field(default_factory=list)
    images_generated: list[dict] = Field(default_factory=list)


# ── Images ──

class ImageOut(BaseModel):
    id: str
    project_id: str
    conversation_id: Optional[str] = None
    prompt: str
    image_url: str
    analysis: Optional[str] = None
    created_at: str


# ── Memory ──

class MemoryEntry(BaseModel):
    id: str
    project_id: str
    category: str
    content: str
    updated_at: str

class MemoryOut(BaseModel):
    memories: list[MemoryEntry]


# ── Agent Tasks ──

class AgentTaskOut(BaseModel):
    id: str
    project_id: str
    task_type: str
    status: str  # pending, running, completed, failed
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

class AgentTriggerResponse(BaseModel):
    task_id: str
    status: str
    message: str
