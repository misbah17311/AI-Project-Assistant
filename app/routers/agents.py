from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.database import get_supabase
from app.models.schemas import AgentTaskOut, AgentTriggerResponse
from app.services.agent_service import run_organize_agent

router = APIRouter(tags=["agents"])


@router.post("/projects/{project_id}/agents/organize", response_model=AgentTriggerResponse)
async def trigger_organize_agent(project_id: str, background_tasks: BackgroundTasks):
    db = get_supabase()

    # verify project exists
    proj = db.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # create the task record
    res = db.table("agent_tasks").insert({
        "project_id": project_id,
        "task_type": "organize",
        "status": "pending",
    }).execute()

    task_id = res.data[0]["id"]

    # fire and forget — runs in the background
    background_tasks.add_task(run_organize_agent, project_id, task_id)

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Organize agent started. Poll the task status endpoint to track progress.",
    }


@router.get("/agent-tasks/{task_id}", response_model=AgentTaskOut)
def get_task_status(task_id: str):
    db = get_supabase()
    res = db.table("agent_tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return res.data[0]


@router.get("/projects/{project_id}/agent-tasks", response_model=list[AgentTaskOut])
def list_project_tasks(project_id: str):
    db = get_supabase()
    res = (
        db.table("agent_tasks")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data
