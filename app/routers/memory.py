from fastapi import APIRouter
from app.services import memory_service
from app.models.schemas import MemoryOut

router = APIRouter(tags=["memory"])


@router.get("/projects/{project_id}/memory", response_model=MemoryOut)
def get_project_memory(project_id: str, category: str = None):
    memories = memory_service.get_memories(project_id, category)
    return {"memories": memories}
