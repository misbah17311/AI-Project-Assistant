# Testing Guide

Step-by-step walkthrough to test every feature. All commands use `curl` so you can run them from any terminal.

Make sure the server is running first:
```bash
uvicorn app.main:app --reload
```

---

## 1. Create a project

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Summer Campaign",
    "description": "Social media ads for a food delivery app",
    "goals": "Increase app downloads by 30% during summer",
    "target_audience": "College students aged 18-24",
    "brand_guidelines": "Bright, energetic colors. Casual tone."
  }'
```

Save the `id` from the response — you'll need it for everything below. I'll use `PROJECT_ID` as placeholder.

## 2. List projects & get a specific one

```bash
# list all
curl http://localhost:8000/projects

# get one
curl http://localhost:8000/projects/PROJECT_ID
```

## 3. Update the project brief

```bash
curl -X PUT http://localhost:8000/projects/PROJECT_ID \
  -H "Content-Type: application/json" \
  -d '{"goals": "Increase app downloads by 30% and grow Instagram following"}'
```

## 4. Start a conversation

```bash
curl -X POST http://localhost:8000/projects/PROJECT_ID/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Initial brainstorm"}'
```

Save the conversation `id` — I'll call it `CONV_ID`.

## 5. Chat with Claude (basic)

```bash
curl -X POST http://localhost:8000/conversations/CONV_ID/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi! Whats a good approach for our summer campaign?"}'
```

Claude should respond with ideas based on the project context. No tools called — just a normal conversation.

## 6. Chat — Claude reads the project brief (tool call)

```bash
curl -X POST http://localhost:8000/conversations/CONV_ID/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Can you check our project brief and summarize what we are working on?"}'
```

Look at `tool_calls_made` in the response — should show `get_project_brief`.

## 7. Chat — generate an image

```bash
curl -X POST http://localhost:8000/conversations/CONV_ID/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Generate an image of a college student ordering food on their phone, bright summer vibes"}'
```

Check `images_generated` in the response — should contain a Pollinations URL. Open it in a browser to see the image (takes a few seconds to render on first load).

## 8. Chat — analyze an image

```bash
curl -X POST http://localhost:8000/conversations/CONV_ID/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze the image we just made. Does it match our brand guidelines?"}'
```

Claude will call `list_project_images` then `analyze_image`. If Gemini's free tier quota is hit, Claude will provide its own analysis based on the image prompt.

## 9. Chat — save memory

```bash
curl -X POST http://localhost:8000/conversations/CONV_ID/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Save a memory that we decided to focus on Instagram Reels as the primary format for our summer campaign"}'
```

Should call `save_project_memory`. Check `tool_calls_made` for confirmation.

## 10. Chat — retrieve memory

```bash
curl -X POST http://localhost:8000/conversations/CONV_ID/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What decisions have we made so far? Check the project memory."}'
```

Should call `get_project_memory` and summarize what's stored.

## 11. List images

```bash
curl http://localhost:8000/projects/PROJECT_ID/images
```

## 12. Get message history

```bash
curl http://localhost:8000/conversations/CONV_ID/messages
```

Shows all messages including user, assistant, and tool messages with the full conversation flow.

## 13. Read project memory directly

```bash
# all categories
curl http://localhost:8000/projects/PROJECT_ID/memory

# specific category
curl "http://localhost:8000/projects/PROJECT_ID/memory?category=decisions"
```

## 14. Trigger the background organize agent

This is the sub-agent that reads everything in the project and creates structured memory.

```bash
curl -X POST http://localhost:8000/projects/PROJECT_ID/agents/organize
```

Save the `task_id` from the response. Then poll it:

```bash
# wait ~15 seconds, then check status
curl http://localhost:8000/agent-tasks/TASK_ID
```

Status goes from `pending` → `running` → `completed`. Once completed, check the memory:

```bash
curl http://localhost:8000/projects/PROJECT_ID/memory
```

Should have organized entries in categories like `brief_summary`, `key_insights`, `decisions`, `action_items`, etc.

## 15. Cross-conversation memory

Start a new conversation and verify Claude has access to memories from before:

```bash
# create second conversation
curl -X POST http://localhost:8000/projects/PROJECT_ID/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Follow-up session"}'

# chat in the new conversation (use new CONV_ID)
curl -X POST http://localhost:8000/conversations/NEW_CONV_ID/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What do you already know about this project from previous sessions?"}'
```

Claude should pull memory and summarize everything — even though this is a brand new conversation.

## 16. List agent tasks

```bash
curl http://localhost:8000/projects/PROJECT_ID/agent-tasks
```

## 17. Delete a project

```bash
curl -X DELETE http://localhost:8000/projects/PROJECT_ID
```

---

## Interactive docs

FastAPI auto-generates interactive API docs. Go to http://localhost:8000/docs in your browser — you can test every endpoint directly from there.

## What to look for

- **Tool loop**: When Claude calls tools, the response includes `tool_calls_made` showing which tools were used. This is the agentic loop — Claude decides when to call tools, executes them, and incorporates results.
- **Multi-tool chains**: Sometimes Claude calls multiple tools in one turn (e.g., list images → analyze image, or save memory → update brief). The response shows all calls made.
- **Memory persistence**: Memory carries across conversations within a project. The organize agent structures it automatically.
- **Background execution**: The organize agent runs asynchronously — you trigger it, get a task ID, and poll for completion.
