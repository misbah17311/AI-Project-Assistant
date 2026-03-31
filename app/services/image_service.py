from openai import OpenAI
from app.config import OPENAI_API_KEY
from app.database import get_supabase

_client = OpenAI(api_key=OPENAI_API_KEY)


async def generate_image(prompt: str, project_id: str, conversation_id: str | None = None) -> dict:
    """
    Generate an image using OpenAI's DALL-E 3.
    Returns the image URL and stores the record in Supabase.
    """
    response = _client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url

    # store in db
    db = get_supabase()
    row = {
        "project_id": project_id,
        "conversation_id": conversation_id,
        "prompt": prompt,
        "image_url": image_url,
    }
    res = db.table("images").insert(row).execute()
    return res.data[0]


def get_project_images(project_id: str) -> list[dict]:
    db = get_supabase()
    res = (
        db.table("images")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data
