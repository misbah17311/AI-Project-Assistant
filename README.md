# AI Project Assistant

An AI-powered project assistant built with FastAPI, Claude, Gemini, and Supabase. Users can chat about their projects, generate and analyze images, and let a background agent organize project knowledge automatically.

**Live Demo:** [https://ai-project-assistant.onrender.com](https://ai-project-assistant.onrender.com)

> Free-tier Render instance — first load may take 30-60 seconds to wake up if it's been idle.

## How it works

The app is structured around **projects**. Each project has a brief (title, goals, audience, etc.), and users can open conversations (chats) within a project. When chatting, Claude has access to tools — it can read/update the project brief, generate images via DALL-E, analyze images with Gemini, and read/write structured memory.

There's also a **background organize agent** — a sub-agent you can trigger via API that pulls all project data (brief, conversations, images), sends it to Claude with a specialized prompt, and writes structured memory entries. This means the assistant "remembers" things across conversations without re-reading everything each time.

## Schema design

Six tables, all linked through project_id:

```
projects ──┬── conversations ──── messages
            ├── images
            ├── project_memories
            └── agent_tasks
```

### projects

The root entity. Brief fields are individual columns rather than a single JSON blob — this lets you query/filter on any field, update one field without touching others, and get column-level validation through Pydantic.

`reference_links` is a Postgres array (`text[]`) instead of a separate table because links are just URLs with no metadata of their own. A join table would be over-normalized for a flat list of strings.

`updated_at` uses a database trigger so it auto-updates on any row change without needing application code to set it.

### conversations

1:N relationship with projects. One project can have many chat sessions (brainstorm, review, follow-up). `ON DELETE CASCADE` so deleting a project cleans up all its conversations automatically.

Why not put messages directly under projects? Conversations create natural boundaries — you can separate "the brainstorm from Monday" from "the review on Friday" instead of mixing 500 messages into one flat list.

### messages

This table is the most critical design decision. The tool loop means a single "turn" can span multiple messages:

```
user:      "Generate an image and analyze it"
assistant: [tool_use: generate_image]          ← no text, just tool call
tool:      [result: image created]
assistant: [tool_use: analyze_image]           ← second tool call
tool:      [result: analysis text]
assistant: "Here's what I found..."            ← final text
```

`role` takes three values: `user`, `assistant`, `tool` — mirroring Anthropic's message format exactly. No translation layer needed when loading conversation history.

`content` is nullable because assistant messages with tool calls have no text (the payload is in the tool_calls column).

`tool_calls` and `tool_results` are JSONB rather than a separate table because: (a) tool calls and parent messages are always accessed together, never independently, (b) a message has 1-3 tool calls at most, so embedded JSONB is simpler than a JOIN, (c) the input structure varies per tool so JSONB handles it naturally.

### images

Linked to both `project_id` (required) and `conversation_id` (optional — an image could be generated outside chat context in the future). `analysis` is stored directly on the image row — each image has at most one Gemini analysis, and caching it here avoids re-calling Gemini.

### project_memories

The key design here is the `UNIQUE(project_id, category)` constraint. This means:
- A project has exactly one entry per category (brief_summary, decisions, key_insights, etc.)
- The organize agent replaces outdated summaries with fresh ones via upsert
- Memory stays clean — no duplicates or stale entries accumulating over time

This was chosen over append-only memory (which would grow noisy) and over a single JSON blob (which can't be queried by category or independently timestamped).

### agent_tasks

Tracks background job execution with a standard state machine: `pending → running → completed/failed`. `result` is JSONB because different task types return different structures. `task_type` defaults to "organize" but supports future agent types without schema changes.

### What I didn't add (and why)

- **No users table** — auth wasn't in scope. Adding one later just means a user_id FK on projects.
- **No separate tool_calls table** — tool calls are always accessed with their parent message, never queried independently. JSONB embedding is simpler.
- **No image_analyses table** — one image gets one analysis. A column on the images table is sufficient.
- **No tags/labels** — could be added as a separate table later if needed, but the current memory categories serve a similar purpose.

## API endpoints

### Projects
- `POST /projects` — create a project with brief info
- `GET /projects` — list all projects
- `GET /projects/{id}` — get a specific project
- `PUT /projects/{id}` — update project brief (partial updates supported, only send fields you want to change)
- `DELETE /projects/{id}` — delete a project (cascades to all related data)

### Conversations & Chat
- `POST /projects/{id}/conversations` — start a new chat session
- `GET /projects/{id}/conversations` — list conversations for a project
- `GET /conversations/{id}/messages` — get full message history including tool call/result messages
- `POST /conversations/{id}/chat` — send a message and get Claude's response (this is the main tool loop endpoint)

### Images
- `GET /projects/{id}/images` — list all generated images for a project

### Memory
- `GET /projects/{id}/memory` — read project memory, optionally filter by category (`?category=decisions`)

### Agents
- `POST /projects/{id}/agents/organize` — trigger the background organize agent
- `GET /agent-tasks/{id}` — poll a task's status
- `GET /projects/{id}/agent-tasks` — list all tasks for a project

## The agent system

### Chat agent (tool loop)

When you send a message to `/conversations/{id}/chat`, here's what happens:

1. User message gets saved to DB
2. We build a system prompt that includes any existing project memory (pre-loaded so Claude always has context)
3. Load conversation history from DB, reconstructing exact Anthropic message format (text blocks, tool_use blocks, tool_result blocks)
4. Send to Claude with 8 tool definitions
5. Claude responds — check the `stop_reason`:
   - `tool_use` → extract tool calls, execute them, save tool results to DB, feed results back to Claude → loop back to step 4
   - `end_turn` → save Claude's text reply to DB, return response to user
6. On the first message of any conversation, Claude proactively checks project memory to ensure it's working with the latest context

The loop has a max of 10 iterations as a safety measure, but in practice Claude usually does 1-3 tool calls then responds.

### Available tools

| Tool | What it does |
|---|---|
| get_project_brief | Reads the project's brief fields from DB |
| update_project_brief | Modifies specific brief fields |
| generate_image | Creates an image via DALL-E 3, stores URL and prompt in DB |
| analyze_image | Downloads image, sends to Gemini for vision analysis, caches result |
| list_project_images | Lists all images generated in the project |
| get_project_memory | Reads stored memory (all categories or filtered) |
| save_project_memory | Writes/updates a memory entry by category (upserts) |
| trigger_organize_agent | Kicks off the background organize agent |

### How image analysis works

Claude can't see images — it only processes text. Gemini acts as Claude's "eyes":
1. Claude decides an image needs analysis and calls `analyze_image`
2. Our code downloads the image bytes from DALL-E's CDN URL
3. Image bytes are sent to Gemini with a vision prompt
4. Gemini returns a text description of what it sees
5. That text goes back to Claude as a tool result
6. Claude interprets the analysis in the context of the project (brand guidelines, target audience, etc.) and writes a meaningful response

### Background organize agent (sub-agent)

A separate agent from the chat agent — it does batch processing rather than real-time interaction. Triggered via API or through the chat (Claude can call `trigger_organize_agent`).

1. Creates a task record (status: pending)
2. Runs in a FastAPI BackgroundTask — doesn't block the API
3. Collects all project data — brief, every conversation with messages, all images, existing memory
4. Sends it to Claude with a specialized "organizer" system prompt
5. Claude reads everything and outputs structured JSON with categories:
   - `brief_summary` — what the project is about
   - `key_insights` — patterns and learnings
   - `decisions` — what's been decided
   - `action_items` — what needs doing
   - `brand_notes` — brand-specific observations
   - `content_ideas` — creative suggestions
   - `open_questions` — unresolved items
6. Each category gets upserted into `project_memories` (replacing any old entry for that category)
7. Task status updated to `completed` (or `failed` with error message)

You poll `/agent-tasks/{id}` to check when it's done. The organized memory is then automatically available to all future conversations through the system prompt.

## Setup

### Option 1: Use the live demo

Just visit [https://ai-project-assistant.onrender.com](https://ai-project-assistant.onrender.com) — no setup needed.

### Option 2: Run locally

1. Clone the repo
```
git clone https://github.com/misbah17311/AI-Project-Assistant.git
cd AI-Project-Assistant
```

2. Install deps:
```
pip install -r requirements.txt
```

3. Create a `.env` file (see `.env.example`):
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=your-gemini-key
```

4. Run the SQL migration in your Supabase dashboard (SQL editor):
```
-- paste contents of supabase_migration.sql
```

5. Run the server:
```
uvicorn app.main:app --reload
```

Frontend at http://localhost:8000 — API docs at http://localhost:8000/docs

## Deployment

Deployed on Render (free tier). The `render.yaml` in the repo configures the service automatically. Environment variables (API keys) are set in the Render dashboard, not committed to git.

## Project structure

```
app/
├── main.py                  # FastAPI app, CORS, router mounting, serves frontend
├── config.py                # env vars and model config
├── database.py              # Supabase client singleton
├── models/
│   └── schemas.py           # Pydantic models for request/response validation
├── routers/
│   ├── projects.py          # Project CRUD
│   ├── conversations.py     # Chat sessions + the main /chat endpoint
│   ├── images.py            # Image listing
│   ├── memory.py            # Memory reading with optional category filter
│   └── agents.py            # Agent trigger + task status polling
├── services/
│   ├── claude_service.py    # Claude API integration, system prompt, tool loop
│   ├── gemini_service.py    # Gemini vision analysis
│   ├── image_service.py     # DALL-E 3 image generation
│   ├── memory_service.py    # Memory CRUD, upsert logic, system prompt formatting
│   └── agent_service.py     # Background organize agent
└── tools/
    ├── definitions.py       # 8 tool schemas in Anthropic's native format
    └── handlers.py          # Tool execution dispatch
static/
└── index.html               # Frontend UI (chat interface, project management)
```

## Tech stack

- **FastAPI** — async web framework with auto-generated API docs
- **Anthropic Claude** (claude-sonnet-4-20250514) — chat agent and organize agent, native tool calling
- **OpenAI DALL-E 3** — image generation (~10-15s per image)
- **Google Gemini** (gemini-2.0-flash) — image analysis via vision API
- **Supabase** (PostgreSQL) — database with Python SDK
- **Pydantic v2** — request/response validation
