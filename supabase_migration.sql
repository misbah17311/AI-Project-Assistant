-- Supabase SQL migration
-- Run this in the Supabase SQL editor to set up all tables

-- projects table
create table if not exists projects (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    description text,
    goals text,
    target_audience text,
    brand_guidelines text,
    reference_links jsonb default '[]'::jsonb,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- conversations - each project can have multiple chat sessions
create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references projects(id) on delete cascade,
    title text default 'New Chat',
    created_at timestamptz default now()
);

-- messages - stores the full chat history
-- role can be 'user', 'assistant', or 'tool'
-- tool_calls/tool_results stored as jsonb so we preserve the full context
create table if not exists messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations(id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'tool')),
    content text,
    tool_calls jsonb,
    tool_results jsonb,
    created_at timestamptz default now()
);

-- images generated through the chat
create table if not exists images (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references projects(id) on delete cascade,
    conversation_id uuid references conversations(id) on delete set null,
    prompt text not null,
    image_url text not null,
    analysis text,
    created_at timestamptz default now()
);

-- per-project memory, organized by category
-- the organize agent writes structured data here
create table if not exists project_memories (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references projects(id) on delete cascade,
    category text not null,
    content text not null,
    updated_at timestamptz default now(),
    unique(project_id, category)
);

-- agent task tracking - so we can poll status
create table if not exists agent_tasks (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references projects(id) on delete cascade,
    task_type text not null default 'organize',
    status text not null default 'pending' check (status in ('pending', 'running', 'completed', 'failed')),
    result jsonb,
    error text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- indexes for common lookups
create index if not exists idx_conversations_project on conversations(project_id);
create index if not exists idx_messages_conversation on messages(conversation_id);
create index if not exists idx_images_project on images(project_id);
create index if not exists idx_memories_project on project_memories(project_id);
create index if not exists idx_agent_tasks_project on agent_tasks(project_id);

-- auto-update the updated_at column on projects
create or replace function update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create or replace trigger projects_updated_at
    before update on projects
    for each row execute function update_updated_at();

create or replace trigger agent_tasks_updated_at
    before update on agent_tasks
    for each row execute function update_updated_at();

create or replace trigger memories_updated_at
    before update on project_memories
    for each row execute function update_updated_at();
