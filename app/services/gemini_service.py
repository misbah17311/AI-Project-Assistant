import httpx
from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.database import get_supabase


def _get_client():
    return genai.Client(api_key=GEMINI_API_KEY)


async def analyze_image(image_id: str, question: str | None = None) -> str:
    """
    Analyze an image using Gemini's vision capabilities.
    Fetches the image from its URL, sends it to Gemini, returns the analysis text.
    """
    db = get_supabase()
    res = db.table("images").select("*").eq("id", image_id).execute()
    if not res.data:
        return "Image not found with that ID."

    image_row = res.data[0]
    image_url = image_row["image_url"]

    # download the image bytes
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http_client:
            img_resp = await http_client.get(image_url)
            img_resp.raise_for_status()
            image_bytes = img_resp.content
            content_type = img_resp.headers.get("content-type", "image/png")
    except Exception as e:
        return f"Couldn't fetch the image: {str(e)}"

    prompt_text = question or "Describe this image in detail. What do you see? What's the style, mood, and key elements?"

    # send to gemini using the types API
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=image_bytes, mime_type=content_type),
                        types.Part.from_text(text=prompt_text),
                    ]
                )
            ],
        )
        analysis_text = response.text
    except Exception as e:
        return f"Gemini analysis failed: {str(e)}"

    # save the analysis back to the image record
    db.table("images").update({"analysis": analysis_text}).eq("id", image_id).execute()

    return analysis_text
