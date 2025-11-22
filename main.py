import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Clients
# Note: In a real production app, you might want to handle missing env vars more gracefully
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: SUPABASE_URL or SUPABASE_KEY not set.")
    supabase: Client = None # type: ignore
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not set.")
    openai_client = None
else:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Prompt-Driven Email Productivity Agent")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class PromptUpdate(BaseModel):
    type: str
    content: str

class EmailQuery(BaseModel):
    query: str

# Default Prompts Data
DEFAULT_PROMPTS = [
    {
        "prompt_type": "categorization",
        "content": "You are an intelligent email assistant. Categorize the following email into one of these categories: Meeting, Newsletter, Spam, Task, Project Update. Return only the category name."
    },
    {
        "prompt_type": "action_item",
        "content": "Extract all action items, tasks, and deadlines from the following email. Return the result as a JSON list of objects with 'task' and 'deadline' fields."
    },
    {
        "prompt_type": "auto_reply",
        "content": "Draft a professional and concise reply to the following email. Address the sender by name if possible and respond to the key points."
    }
]

@app.post("/init-prompts")
async def init_prompts():
    """
    Checks if the prompts table is empty, and if so, inserts default prompts.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    try:
        # Check if prompts table is empty
        # We fetch 1 record to see if any exist
        response = supabase.table("prompts").select("id", count="exact").limit(1).execute()
        
        # The count is usually returned in the response object if count='exact' is used
        # However, checking the length of data is also a safe fallback for 'is empty' check
        if response.count and response.count > 0:
             return {"message": "Prompts table is not empty. Initialization skipped."}

        # Insert default prompts
        insert_response = supabase.table("prompts").insert(DEFAULT_PROMPTS).execute()
        
        return {
            "message": "Default prompts initialized successfully.",
            "data": insert_response.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/")
async def root():
    return {"message": "API is running"}
