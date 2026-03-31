import json
from app.database import get_supabase
from app.services import image_service, gemini_service, memory_service

# this gets set by the chat router so tool handlers can schedule background work
_background_tasks = None


def set_background_tasks(bg):
    global _background_tasks
    _background_tasks = bg


async def handle_tool_call(tool_name: str, tool_input: dict, project_id: str, conversation_id: str) -> str:
    """
    Dispatch a tool call to the right handler.
    Returns a string result that gets sent back to Claude.
    """
    try:
        if tool_name == "get_project_brief":
            return _get_project_brief(project_id)

        elif tool_name == "update_project_brief":
            return _update_project_brief(project_id, tool_input)

        elif tool_name == "generate_image":
            result = await image_service.generate_image(
                prompt=tool_input["prompt"],
                project_id=project_id,
                conversation_id=conversation_id,
            )
            return json.dumps({
                "image_id": result["id"],
                "url": result["image_url"],
                "prompt": result["prompt"],
            })

        elif tool_name == "analyze_image":
            analysis = await gemini_service.analyze_image(
                image_id=tool_input["image_id"],
                question=tool_input.get("question"),
            )
            return analysis

        elif tool_name == "list_project_images":
            images = image_service.get_project_images(project_id)
            # return a compact version
            summary = [
                {"id": img["id"], "prompt": img["prompt"], "url": img["image_url"], "has_analysis": bool(img.get("analysis"))}
                for img in images
            ]
            return json.dumps(summary)

        elif tool_name == "get_project_memory":
            category = tool_input.get("category")
            memories = memory_service.get_memories(project_id, category)
            if not memories:
                return "No memories stored yet for this project."
            formatted = [{"category": m["category"], "content": m["content"]} for m in memories]
            return json.dumps(formatted)

        elif tool_name == "save_project_memory":
            result = memory_service.save_memory(
                project_id=project_id,
                category=tool_input["category"],
                content=tool_input["content"],
            )
            return f"Saved to memory under '{result['category']}'"

        elif tool_name == "trigger_organize_agent":
            return _trigger_organize(project_id)

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        return f"Tool error ({tool_name}): {str(e)}"


def _get_project_brief(project_id: str) -> str:
    db = get_supabase()
    res = db.table("projects").select("*").eq("id", project_id).execute()
    if not res.data:
        return "Project not found."
    project = res.data[0]
    return json.dumps({
        "title": project["title"],
        "description": project.get("description"),
        "goals": project.get("goals"),
        "target_audience": project.get("target_audience"),
        "brand_guidelines": project.get("brand_guidelines"),
        "reference_links": project.get("reference_links", []),
    })


def _update_project_brief(project_id: str, updates: dict) -> str:
    db = get_supabase()
    # filter out None values
    clean = {k: v for k, v in updates.items() if v is not None}
    if not clean:
        return "No fields provided to update."
    db.table("projects").update(clean).eq("id", project_id).execute()
    return f"Updated project brief: {', '.join(clean.keys())}"


def _trigger_organize(project_id: str) -> str:
    """Create an agent task record and kick off the background agent if possible."""
    from app.services.agent_service import run_organize_agent

    db = get_supabase()
    res = db.table("agent_tasks").insert({
        "project_id": project_id,
        "task_type": "organize",
        "status": "pending",
    }).execute()
    task_id = res.data[0]["id"]

    # schedule background work if we have a BackgroundTasks reference
    if _background_tasks is not None:
        _background_tasks.add_task(run_organize_agent, project_id, task_id)

    return json.dumps({"task_id": task_id, "status": "pending", "message": "Organize agent has been queued. The user can check progress with the task ID."})
