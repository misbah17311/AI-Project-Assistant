from fastapi import APIRouter
from app.services import image_service
from app.models.schemas import ImageOut

router = APIRouter(tags=["images"])


@router.get("/projects/{project_id}/images", response_model=list[ImageOut])
def list_images(project_id: str):
    return image_service.get_project_images(project_id)
