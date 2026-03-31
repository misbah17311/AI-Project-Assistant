from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.database import get_supabase
from app.models.schemas import (
    ConversationCreate, ConversationOut, MessageOut,
    ChatRequest, ChatResponse,
)
from app.services import claude_service
from app.tools.handlers import set_background_tasks

router = APIRouter(tags=["conversations"])


@router.post("/projects/{project_id}/conversations", response_model=ConversationOut)
def create_conversation(project_id: str, data: ConversationCreate):
    db = get_supabase()

    # make sure the project exists
    proj = db.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")

    res = db.table("conversations").insert({
        "project_id": project_id,
        "title": data.title,
    }).execute()
    return res.data[0]


@router.get("/projects/{project_id}/conversations", response_model=list[ConversationOut])
def list_conversations(project_id: str):
    db = get_supabase()
    res = (
        db.table("conversations")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: str):
    db = get_supabase()
    res = (
        db.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return res.data


@router.post("/conversations/{conversation_id}/chat", response_model=ChatResponse)
async def chat(conversation_id: str, data: ChatRequest, background_tasks: BackgroundTasks):
    db = get_supabase()

    # figure out which project this conversation belongs to
    conv = db.table("conversations").select("project_id").eq("id", conversation_id).execute()
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    project_id = conv.data[0]["project_id"]

    # let tool handlers schedule background work if needed
    set_background_tasks(background_tasks)

    result = await claude_service.chat(
        project_id=project_id,
        conversation_id=conversation_id,
        user_message=data.message,
    )
    return result
