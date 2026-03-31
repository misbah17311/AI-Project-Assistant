import json
import anthropic
from app.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from app.tools.definitions import TOOLS
from app.tools.handlers import handle_tool_call
from app.services.memory_service import format_memories_for_context
from app.database import get_supabase

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT_BASE = """You are an AI project assistant. You help users manage their creative projects — brainstorming ideas, organizing information, generating images, and keeping track of decisions.

You have access to tools for:
- Reading and updating the project brief
- Generating images and analyzing them
- Storing and retrieving project memory
- Triggering a background agent to organize all project knowledge

IMPORTANT: At the start of every conversation, you MUST call get_project_memory to check for any stored knowledge before responding to the user. Always do this on your first response in a conversation, even if memory context is shown above — this demonstrates to the user that you are actively checking project knowledge. After the first message, you don't need to call it again unless the user asks about memories or past context.

When the user asks for something that needs a tool, use the tool rather than guessing. After receiving tool results, always provide a clear and helpful summary to the user."""


def _build_system_prompt(project_id: str) -> str:
    memory_context = format_memories_for_context(project_id)
    if memory_context:
        return f"{SYSTEM_PROMPT_BASE}\n\n---\n{memory_context}"
    return SYSTEM_PROMPT_BASE


def _load_conversation_history(conversation_id: str) -> list[dict]:
    """Pull past messages from DB and format them for Anthropic's messages API."""
    db = get_supabase()
    res = (
        db.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )

    messages = []
    for row in res.data:
        if row["role"] == "user":
            messages.append({"role": "user", "content": row["content"] or ""})

        elif row["role"] == "assistant":
            content_blocks = []
            if row.get("content"):
                content_blocks.append({"type": "text", "text": row["content"]})
            if row.get("tool_calls"):
                for tc in row["tool_calls"]:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["input"],
                    })
            if content_blocks:
                messages.append({"role": "assistant", "content": content_blocks})

        elif row["role"] == "tool":
            if row.get("tool_results"):
                content_blocks = []
                for tr in row["tool_results"]:
                    content_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": tr["tool_use_id"],
                        "content": tr["content"],
                    })
                messages.append({"role": "user", "content": content_blocks})

    return messages


def _save_message(conversation_id: str, role: str, content: str = None, tool_calls=None, tool_results=None):
    db = get_supabase()
    row = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
    }
    db.table("messages").insert(row).execute()


def _call_claude(messages: list[dict], system: str) -> anthropic.types.Message:
    """Make a direct call to Claude via the Anthropic SDK."""
    return client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=system,
        tools=TOOLS,
        messages=messages,
    )


async def chat(project_id: str, conversation_id: str, user_message: str) -> dict:
    """
    Main agentic chat loop. Sends user message to Claude, handles tool calls
    in a loop until we get a final text response.
    """
    _save_message(conversation_id, "user", content=user_message)

    system = _build_system_prompt(project_id)
    messages = _load_conversation_history(conversation_id)

    tool_calls_made = []
    images_generated = []

    max_iterations = 10
    for _ in range(max_iterations):
        response = _call_claude(messages, system)

        # extract text and tool_use blocks from the response
        text_parts = []
        tool_use_blocks = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_use_blocks.append(block)

        assistant_text = "\n".join(text_parts) if text_parts else ""

        if response.stop_reason == "tool_use" and tool_use_blocks:
            # store assistant message with tool calls
            stored_tool_calls = []
            for block in tool_use_blocks:
                stored_tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

            _save_message(conversation_id, "assistant", content=assistant_text, tool_calls=stored_tool_calls)

            # reconstruct assistant content blocks for the API
            assistant_content = []
            if assistant_text:
                assistant_content.append({"type": "text", "text": assistant_text})
            for block in tool_use_blocks:
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
            messages.append({"role": "assistant", "content": assistant_content})

            # execute each tool and collect results
            tool_result_blocks = []
            tool_result_entries = []

            for block in tool_use_blocks:
                result = await handle_tool_call(
                    tool_name=block.name,
                    tool_input=block.input,
                    project_id=project_id,
                    conversation_id=conversation_id,
                )

                tool_calls_made.append({
                    "tool": block.name,
                    "input": block.input,
                    "result_preview": result[:200] if result else "",
                })

                if block.name == "generate_image" and result:
                    try:
                        img_data = json.loads(result)
                        images_generated.append(img_data)
                    except Exception:
                        pass

                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result or "",
                })
                tool_result_entries.append({
                    "tool_use_id": block.id,
                    "content": result or "",
                })

            # tool results go as a "user" message in Anthropic's format
            messages.append({"role": "user", "content": tool_result_blocks})
            _save_message(conversation_id, "tool", tool_results=tool_result_entries)

        else:
            # final text response (stop_reason == "end_turn")
            _save_message(conversation_id, "assistant", content=assistant_text)
            return {
                "reply": assistant_text,
                "tool_calls_made": tool_calls_made,
                "images_generated": images_generated,
            }

    return {
        "reply": "I made several tool calls but couldn't form a final response. Please try again.",
        "tool_calls_made": tool_calls_made,
        "images_generated": images_generated,
    }
