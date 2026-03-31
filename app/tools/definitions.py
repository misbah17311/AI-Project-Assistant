# tool schemas in Anthropic's native format
# each tool is something Claude can decide to call during a conversation

TOOLS = [
    {
        "name": "get_project_brief",
        "description": "Retrieve the full project brief including title, description, goals, target audience, brand guidelines, and reference links. Use this when you need context about the current project.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "update_project_brief",
        "description": "Update specific fields of the project brief. Only include the fields you want to change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "New project title"},
                "description": {"type": "string", "description": "Updated project description"},
                "goals": {"type": "string", "description": "Updated project goals"},
                "target_audience": {"type": "string", "description": "Updated target audience info"},
                "brand_guidelines": {"type": "string", "description": "Updated brand guidelines"},
                "reference_links": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated list of reference URLs",
                },
            },
            "required": [],
        },
    },
    {
        "name": "generate_image",
        "description": "Generate an image based on a text prompt. The image will be saved to the project. Use this when the user asks you to create, generate, or make an image/visual.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed description of the image to generate",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "analyze_image",
        "description": "Analyze an existing image using Gemini vision. Provide the image ID from the project's image list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_id": {
                    "type": "string",
                    "description": "UUID of the image to analyze",
                },
                "question": {
                    "type": "string",
                    "description": "Specific question about the image, or leave empty for a general analysis",
                },
            },
            "required": ["image_id"],
        },
    },
    {
        "name": "list_project_images",
        "description": "Get a list of all images that have been generated for this project.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_project_memory",
        "description": "Read the project's stored memory/knowledge base. This contains organized information from previous conversations and the organize agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional - fetch a specific category like 'brief_summary', 'key_insights', 'decisions', etc. Leave empty to get all.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "save_project_memory",
        "description": "Save or update a piece of knowledge in the project's memory. Use categories to organize info logically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category name like 'brief_summary', 'key_insights', 'decisions', 'action_items', 'brand_notes'",
                },
                "content": {
                    "type": "string",
                    "description": "The content to store under this category",
                },
            },
            "required": ["category", "content"],
        },
    },
    {
        "name": "trigger_organize_agent",
        "description": "Kick off the background organize agent. It will go through all project data (brief, conversations, images) and create structured memory entries. Returns a task ID you can share with the user for tracking.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
