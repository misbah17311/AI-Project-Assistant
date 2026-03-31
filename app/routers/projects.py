from fastapi import APIRouter, HTTPException
from app.database import get_supabase
from app.models.schemas import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut)
def create_project(data: ProjectCreate):
    db = get_supabase()
    row = {
        "title": data.title,
        "description": data.description,
        "goals": data.goals,
        "target_audience": data.target_audience,
        "brand_guidelines": data.brand_guidelines,
        "reference_links": data.reference_links or [],
    }
    res = db.table("projects").insert(row).execute()
    return res.data[0]


@router.get("", response_model=list[ProjectOut])
def list_projects():
    db = get_supabase()
    res = db.table("projects").select("*").order("created_at", desc=True).execute()
    return res.data


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str):
    db = get_supabase()
    res = db.table("projects").select("*").eq("id", project_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return res.data[0]


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, data: ProjectUpdate):
    db = get_supabase()

    # only send fields that were actually provided
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    res = db.table("projects").update(updates).eq("id", project_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return res.data[0]


@router.delete("/{project_id}")
def delete_project(project_id: str):
    db = get_supabase()
    res = db.table("projects").delete().eq("id", project_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Deleted", "id": project_id}
