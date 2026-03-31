from app.database import get_supabase


def get_memories(project_id: str, category: str | None = None) -> list[dict]:
    db = get_supabase()
    query = db.table("project_memories").select("*").eq("project_id", project_id)
    if category:
        query = query.eq("category", category)
    res = query.order("updated_at", desc=True).execute()
    return res.data


def save_memory(project_id: str, category: str, content: str) -> dict:
    """
    Upsert a memory entry. If the category already exists for this project,
    we update it instead of creating a duplicate.
    """
    db = get_supabase()

    # check if this category already exists
    existing = (
        db.table("project_memories")
        .select("id")
        .eq("project_id", project_id)
        .eq("category", category)
        .execute()
    )

    if existing.data:
        # update existing
        res = (
            db.table("project_memories")
            .update({"content": content})
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        # create new
        res = (
            db.table("project_memories")
            .insert({"project_id": project_id, "category": category, "content": content})
            .execute()
        )

    return res.data[0]


def format_memories_for_context(project_id: str) -> str:
    """Build a text block of all memories to inject into the system prompt."""
    memories = get_memories(project_id)
    if not memories:
        return ""

    lines = ["Here's what you know about this project from memory:\n"]
    for m in memories:
        lines.append(f"[{m['category']}]\n{m['content']}\n")
    return "\n".join(lines)
