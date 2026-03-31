import json
import anthropic
from app.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from app.database import get_supabase
from app.services.memory_service import save_memory

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

ORGANIZE_PROMPT = """You are a project knowledge organizer. You'll receive all the data from a project — brief, conversations, images, and existing memory.

Your job is to analyze everything and produce structured memory entries. Output a JSON array where each item has:
- "category": a clear label (use these categories: brief_summary, key_insights, decisions, action_items, brand_notes, content_ideas, open_questions)
- "content": well-organized text summarizing what you found

Only include categories where there's actually something meaningful to say. Be thorough but not verbose. Focus on actionable, useful info that would help someone picking up this project understand what's happened so far.

Respond with ONLY the JSON array, nothing else."""


async def run_organize_agent(project_id: str, task_id: str):
    """
    Background sub-agent. Pulls all project data, sends to Claude
    with the organize prompt, writes structured memory entries.
    """
    db = get_supabase()

    db.table("agent_tasks").update({"status": "running"}).eq("id", task_id).execute()

    try:
        project_data = _collect_project_data(project_id)

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=ORGANIZE_PROMPT,
            messages=[
                {"role": "user", "content": f"Here's all the data from the project. Analyze and organize it:\n\n{json.dumps(project_data, indent=2, default=str)}"},
            ],
        )

        response_text = response.content[0].text

        # parse the JSON -- sometimes it's wrapped in code blocks
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        memories = json.loads(cleaned)

        for entry in memories:
            save_memory(
                project_id=project_id,
                category=entry["category"],
                content=entry["content"],
            )

        db.table("agent_tasks").update({
            "status": "completed",
            "result": {"categories_updated": [m["category"] for m in memories]},
        }).eq("id", task_id).execute()

    except Exception as e:
        db.table("agent_tasks").update({
            "status": "failed",
            "error": str(e),
        }).eq("id", task_id).execute()


def _collect_project_data(project_id: str) -> dict:
    """Pull everything we know about this project."""
    db = get_supabase()

    project = db.table("projects").select("*").eq("id", project_id).execute().data
    conversations = db.table("conversations").select("*").eq("project_id", project_id).execute().data
    images = db.table("images").select("*").eq("project_id", project_id).execute().data
    memories = db.table("project_memories").select("*").eq("project_id", project_id).execute().data

    all_messages = []
    for conv in conversations:
        msgs = (
            db.table("messages")
            .select("role, content, created_at")
            .eq("conversation_id", conv["id"])
            .order("created_at")
            .execute()
        )
        for m in msgs.data:
            if m.get("content"):
                all_messages.append({
                    "conversation": conv.get("title", "Untitled"),
                    "role": m["role"],
                    "content": m["content"],
                })

    return {
        "project": project[0] if project else None,
        "conversations_count": len(conversations),
        "messages": all_messages,
        "images": [{"prompt": i["prompt"], "analysis": i.get("analysis")} for i in images],
        "existing_memory": [{"category": m["category"], "content": m["content"]} for m in memories],
    }
