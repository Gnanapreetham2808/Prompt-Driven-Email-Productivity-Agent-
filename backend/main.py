import os
import json
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

class PromptContentUpdate(BaseModel):
    content: str

class AgentChatRequest(BaseModel):
    email_id: str
    user_query: str

class DraftRequest(BaseModel):
    email_id: str

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

@app.post("/ingest")
async def ingest_emails():
    """
    Ingests emails from mock_inbox.json, analyzes them using OpenAI,
    and stores the results in Supabase.
    """
    if not supabase or not openai_client:
        raise HTTPException(status_code=500, detail="Services not initialized")

    try:
        # Load mock emails
        try:
            with open("mock_inbox.json", "r") as f:
                emails = json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="mock_inbox.json not found")

        results = []
        
        for email in emails:
            # 1. Insert email into Supabase
            email_data = {
                "sender": email["sender"],
                "subject": email["subject"],
                "body": email["body"],
                "received_at": email["timestamp"],
                "is_read": False
            }
            
            # Insert and get the new record to get the UUID
            res = supabase.table("emails").insert(email_data).execute()
            if not res.data:
                print(f"Failed to insert email: {email.get('subject')}")
                continue
                
            new_email_id = res.data[0]['id']

            # 2. CRITICAL: Fetch prompts inside the loop
            # We fetch the latest prompts for every email as requested
            cat_prompt_res = supabase.table("prompts").select("content").eq("prompt_type", "categorization").execute()
            action_prompt_res = supabase.table("prompts").select("content").eq("prompt_type", "action_item").execute()
            
            # Use fetched content or fallbacks
            cat_prompt = cat_prompt_res.data[0]['content'] if cat_prompt_res.data else "Categorize this email."
            action_prompt = action_prompt_res.data[0]['content'] if action_prompt_res.data else "Extract tasks."

            # 3. Analyze with OpenAI
            system_prompt = f"""
            You are an email analysis engine.
            
            Task 1 (Categorization): {cat_prompt}
            Task 2 (Action Items): {action_prompt}
            
            Output Format: Return a valid JSON object with exactly these keys:
            - "category": string (e.g., "Meeting", "Newsletter", "Spam", "Task", "Project Update")
            - "extracted_tasks": list of objects, where each object has "task" (string) and "deadline" (string or null).
            """
            
            try:
                completion = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": email["body"]}
                    ],
                    response_format={"type": "json_object"}
                )
                
                analysis_content = completion.choices[0].message.content
                analysis_json = json.loads(analysis_content)
                
                # 4. Insert into email_analysis
                analysis_data = {
                    "email_id": new_email_id,
                    "category": analysis_json.get("category"),
                    "extracted_tasks": analysis_json.get("extracted_tasks"),
                    # analysis_date defaults to NOW() in DB, but we can send it if needed
                }
                
                supabase.table("email_analysis").insert(analysis_data).execute()
                results.append({"email_id": new_email_id, "status": "analyzed"})
                
            except Exception as ai_error:
                print(f"AI Analysis failed for email {new_email_id}: {ai_error}")
                results.append({"email_id": new_email_id, "status": "ingested_only", "error": str(ai_error)})

        return {"message": "Ingestion process completed", "processed_count": len(results), "details": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.get("/prompts")
async def get_prompts():
    """
    Fetches all system prompts from the database.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        response = supabase.table("prompts").select("*").order("created_at").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, update: PromptContentUpdate):
    """
    Updates a specific prompt's content.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    try:
        response = supabase.table("prompts").update({"content": update.content}).eq("id", prompt_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails")
async def get_emails():
    """
    Fetches all emails with their analysis.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        # Fetch emails and join with analysis if possible, or just fetch emails for now
        # Supabase-py join syntax can be tricky, let's just fetch emails and analysis separately or use a view if we had one.
        # For simplicity, let's just fetch emails.
        response = supabase.table("emails").select("*, email_analysis(category, extracted_tasks)").order("received_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/chat")
async def agent_chat(request: AgentChatRequest):
    """
    Chat with the agent about a specific email.
    """
    if not supabase or not openai_client:
        raise HTTPException(status_code=500, detail="Services not initialized")

    try:
        # 1. Fetch Email Body
        email_res = supabase.table("emails").select("body, sender, subject").eq("id", request.email_id).execute()
        if not email_res.data:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email = email_res.data[0]
        
        # 2. Fetch System Prompt (Try 'general_agent', fallback to generic)
        # We can also allow the user to create a 'general_agent' prompt in the UI later.
        prompt_res = supabase.table("prompts").select("content").eq("prompt_type", "general_agent").execute()
        
        if prompt_res.data:
            system_instruction = prompt_res.data[0]['content']
        else:
            system_instruction = "You are a helpful AI assistant. You are analyzing the following email. Answer the user's questions based on the email content."

        # Construct the full system message
        system_message = f"""
        {system_instruction}

        --- EMAIL CONTEXT ---
        From: {email['sender']}
        Subject: {email['subject']}
        Body:
        {email['body']}
        ---------------------
        """

        # 3. Call OpenAI
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": request.user_query}
            ]
        )
        
        return {"response": completion.choices[0].message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/draft")
async def generate_draft(request: DraftRequest):
    """
    Generates a draft reply for an email and saves it to the database.
    """
    if not supabase or not openai_client:
        raise HTTPException(status_code=500, detail="Services not initialized")

    try:
        # 1. Fetch Email
        email_res = supabase.table("emails").select("body, sender, subject").eq("id", request.email_id).execute()
        if not email_res.data:
            raise HTTPException(status_code=404, detail="Email not found")
        email = email_res.data[0]

        # 2. Fetch 'auto_reply' Prompt
        prompt_res = supabase.table("prompts").select("content").eq("prompt_type", "auto_reply").execute()
        if prompt_res.data:
            system_instruction = prompt_res.data[0]['content']
        else:
            system_instruction = "Draft a professional reply to this email."

        # 3. Call OpenAI
        system_prompt = f"""
        {system_instruction}
        
        Output Format: Return a valid JSON object with exactly these keys:
        - "draft_subject": string
        - "draft_body": string
        """

        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"From: {email['sender']}\nSubject: {email['subject']}\nBody:\n{email['body']}"}
            ],
            response_format={"type": "json_object"}
        )

        draft_content = completion.choices[0].message.content
        draft_json = json.loads(draft_content)

        # 4. Insert into drafts table
        draft_data = {
            "email_id": request.email_id,
            "draft_subject": draft_json.get("draft_subject"),
            "draft_body": draft_json.get("draft_body")
        }
        
        insert_res = supabase.table("drafts").insert(draft_data).execute()
        
        return {"message": "Draft generated successfully", "draft": insert_res.data[0]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
