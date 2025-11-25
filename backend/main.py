import os
import json
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from openai import OpenAI
from dotenv import load_dotenv
from collections import Counter
from gmail_sync import GmailSync
from fastapi.responses import RedirectResponse, HTMLResponse
from datetime import datetime

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

# Initialize Gmail Sync
gmail_sync = GmailSync()

# Note: For production, create user_tokens table in Supabase:
# CREATE TABLE IF NOT EXISTS user_tokens (
#     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
#     user_email TEXT UNIQUE NOT NULL,
#     token_data JSONB NOT NULL,
#     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
#     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
# );

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
    language: Optional[str] = None  # Optional target language for response

class DraftRequest(BaseModel):
    email_id: str
    language: Optional[str] = None  # Optional target language for draft

class TasksUpdate(BaseModel):
    tasks: List[dict]  # Each dict: {"task": str, "deadline": Optional[str], "completed": bool}

class CategoryUpdate(BaseModel):
    category: str

class StarToggle(BaseModel):
    starred: bool

# Default Prompts Data
DEFAULT_PROMPTS = [
    {
        "prompt_type": "categorization",
        "content": """Analyze this email and categorize it into ONE of these categories: 
- "Urgent Task" (requires immediate action)
- "Meeting" (meeting invitations, calendar items)
- "Project Update" (status updates, sprint reviews)
- "Newsletter" (marketing emails, digests, weekly roundups)
- "Notification" (automated system notifications, alerts)
- "Client Communication" (emails from clients/partners)
- "Spam" (promotional, suspicious, irrelevant)
- "General" (everything else)

Choose the MOST SPECIFIC category that applies."""
    },
    {
        "prompt_type": "action_item",
        "content": """Extract actionable tasks from this email. For each task, identify:
- The specific action to be taken
- Any deadline or due date mentioned (if any)

Only return tasks that require the recipient to DO something.
Ignore informational content or passive updates.

Return empty list if no action items exist."""
    },
    {
        "prompt_type": "auto_reply",
        "content": """Draft a professional, concise reply to this email. 

Guidelines:
- Be polite and professional
- Address the main points from the original email
- Keep it brief (2-3 paragraphs maximum)
- Use appropriate tone based on sender and context
- End with a clear call-to-action or next steps if needed
- Do not make up information - only respond based on the email content"""
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
    return {"message": "Email Productivity Agent API is running", "docs": "/docs"}

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring"""
    return {
        "status": "healthy",
        "supabase": "connected" if supabase else "disconnected",
        "openai": "connected" if openai_client else "disconnected"
    }

@app.get("/analytics/dashboard")
async def get_dashboard_analytics():
    """
    Get comprehensive email analytics for dashboard display
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        # Fetch all data
        emails_res = supabase.table("emails").select("*").execute()
        analysis_res = supabase.table("email_analysis").select("*").execute()
        drafts_res = supabase.table("drafts").select("*").execute()
        
        emails = emails_res.data
        analyses = analysis_res.data
        drafts = drafts_res.data
        
        # Calculate statistics
        total_emails = len(emails)
        total_analyzed = len(analyses)
        total_drafts = len(drafts)
        
        # Category breakdown
        categories = [a.get('category', 'Uncategorized') for a in analyses]
        category_counts = dict(Counter(categories))
        
        # Action items count
        total_tasks = sum(len(a.get('extracted_tasks', [])) for a in analyses if a.get('extracted_tasks'))
        
        # Sender statistics
        sender_counts = dict(Counter([e.get('sender') for e in emails]))
        top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Unread count
        unread_count = sum(1 for e in emails if not e.get('is_read', False))
        
        return {
            "total_emails": total_emails,
            "analyzed_emails": total_analyzed,
            "unread_emails": unread_count,
            "total_drafts": total_drafts,
            "total_action_items": total_tasks,
            "category_breakdown": category_counts,
            "top_senders": [{"email": sender, "count": count} for sender, count in top_senders],
            "analysis_rate": round((total_analyzed / total_emails * 100) if total_emails > 0 else 0, 1)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/search")
async def search_emails(q: str = ""):
    """
    Search emails by sender, subject, or body content
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        if not q:
            return []
        
        # Search across multiple fields
        response = supabase.table("emails").select("*, email_analysis(category, extracted_tasks)").or_(
            f"sender.ilike.%{q}%,subject.ilike.%{q}%,body.ilike.%{q}%"
        ).order("received_at", desc=True).execute()
        
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/unread-count")
async def unread_count():
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    try:
        res = supabase.table("emails").select("id,is_read").execute()
        count = sum(1 for e in res.data if not e.get("is_read", False))
        return {"unread": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/filter")
async def filter_emails(category: Optional[str] = None, unread: Optional[bool] = None, starred: Optional[bool] = None):
    """Filter emails locally by joined analysis category, unread status, starred flag."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    try:
        res = supabase.table("emails").select("*, email_analysis(category, previous_category, extracted_tasks)").order("received_at", desc=True).execute()
        data = res.data or []
        filtered = []
        for e in data:
            analysis = e.get("email_analysis") or {}
            cat_ok = True if category is None else (analysis.get("category") == category)
            unread_ok = True if unread is None else ((not e.get("is_read", False)) == unread)
            starred_ok = True if starred is None else (e.get("is_starred", False) == starred)
            if cat_ok and unread_ok and starred_ok:
                filtered.append(e)
        return filtered
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
                "is_read": False,
                "is_starred": False,
                "attachments": email.get("attachments", [])
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
                # Normalize tasks adding completion flag
                raw_tasks = analysis_json.get("extracted_tasks") or []
                tasks_with_status = []
                for t in raw_tasks:
                    if isinstance(t, dict):
                        tasks_with_status.append({
                            "task": t.get("task"),
                            "deadline": t.get("deadline"),
                            "completed": False
                        })
                    else:
                        # If the model returned a plain string list fallback
                        tasks_with_status.append({
                            "task": str(t),
                            "deadline": None,
                            "completed": False
                        })

                analysis_data = {
                    "email_id": new_email_id,
                    "category": analysis_json.get("category"),
                    "extracted_tasks": tasks_with_status,
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
    Fetches all emails with their analysis. If database is empty, returns mock data.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        # Fetch emails from database
        response = supabase.table("emails").select("*, email_analysis(category, previous_category, extracted_tasks)").order("received_at", desc=True).execute()
        
        # If database is empty, return mock emails
        if not response.data or len(response.data) == 0:
            try:
                with open("mock_inbox.json", "r") as f:
                    mock_emails = json.load(f)
                # Transform mock format to match database format with pre-defined categories
                return [{
                    "id": str(email.get("id")),
                    "sender": email.get("sender"),
                    "subject": email.get("subject"),
                    "body": email.get("body"),
                    "received_at": email.get("timestamp"),
                    "is_read": email.get("is_read", False),
                    "is_starred": email.get("is_starred", False),
                    "attachments": email.get("attachments", []),
                    "email_analysis": [{"category": email.get("category", "General"), "extracted_tasks": []}] if email.get("category") else []
                } for email in mock_emails]
            except FileNotFoundError:
                return []
        
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/emails/{email_id}/star")
async def star_email(email_id: str):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    try:
        # Try database first
        res = supabase.table("emails").update({"is_starred": True}).eq("id", email_id).execute()
        if res.data:
            return {"message": "Email starred", "data": res.data}
        
        # If not in database, update mock data
        with open("mock_inbox.json", "r") as f:
            mock_emails = json.load(f)
        
        for email in mock_emails:
            if str(email.get("id")) == email_id:
                email["is_starred"] = True
                break
        
        with open("mock_inbox.json", "w") as f:
            json.dump(mock_emails, f, indent=2)
        
        return {"message": "Email starred", "data": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/emails/{email_id}/unstar")
async def unstar_email(email_id: str):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    try:
        # Try database first
        res = supabase.table("emails").update({"is_starred": False}).eq("id", email_id).execute()
        if res.data:
            return {"message": "Email unstarred", "data": res.data}
        
        # If not in database, update mock data
        with open("mock_inbox.json", "r") as f:
            mock_emails = json.load(f)
        
        for email in mock_emails:
            if str(email.get("id")) == email_id:
                email["is_starred"] = False
                break
        
        with open("mock_inbox.json", "w") as f:
            json.dump(mock_emails, f, indent=2)
        
        return {"message": "Email unstarred", "data": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/emails/{email_id}/tasks")
async def update_tasks(email_id: str, update: TasksUpdate):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    try:
        # Ensure tasks structure validity minimally
        normalized = []
        for t in update.tasks:
            if not isinstance(t, dict):
                continue
            normalized.append({
                "task": t.get("task"),
                "deadline": t.get("deadline"),
                "completed": bool(t.get("completed", False))
            })
        res = supabase.table("email_analysis").update({"extracted_tasks": normalized}).eq("email_id", email_id).execute()
        return {"message": "Tasks updated", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/emails/{email_id}/category")
async def update_category(email_id: str, update: CategoryUpdate):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    try:
        # Fetch existing analysis row
        existing = supabase.table("email_analysis").select("id, category").eq("email_id", email_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Analysis not found for email")
        row = existing.data[0]
        res = supabase.table("email_analysis").update({
            "previous_category": row.get("category"),
            "category": update.category
        }).eq("id", row.get("id")).execute()
        return {"message": "Category updated", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/emails/{email_id}/undo-category")
async def undo_category(email_id: str):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    try:
        existing = supabase.table("email_analysis").select("id, category, previous_category").eq("email_id", email_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Analysis not found for email")
        row = existing.data[0]
        prev = row.get("previous_category")
        if not prev:
            raise HTTPException(status_code=400, detail="No previous category to revert to")
        res = supabase.table("email_analysis").update({
            "category": prev,
            "previous_category": None
        }).eq("id", row.get("id")).execute()
        return {"message": "Category reverted", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/prompt-templates")
async def prompt_templates():
    # Static library of prompt templates for user selection
    templates = [
        {"prompt_type": "categorization", "name": "Concise Categorization", "content": "Classify the email into: Meeting | Newsletter | Spam | Task | Project Update. Respond with one word."},
        {"prompt_type": "action_item", "name": "Detailed Task Extraction", "content": "Extract actionable tasks with any deadlines; return JSON [{task, deadline}]."},
        {"prompt_type": "auto_reply", "name": "Friendly Follow-Up", "content": "Write a warm, concise follow-up acknowledging receipt and next steps."},
        {"prompt_type": "general_agent", "name": "Analyst", "content": "Answer questions about the email focusing on facts and tasks."}
    ]
    return templates

@app.post("/agent/chat")
async def agent_chat(request: AgentChatRequest):
    """
    Chat with the agent about a specific email.
    """
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")

    try:
        # 1. Fetch Email (try database first, then mock data)
        email = None
        
        # Try database only if email_id looks like a UUID
        if supabase and len(str(request.email_id)) > 10 and '-' in str(request.email_id):
            try:
                email_res = supabase.table("emails").select("body, sender, subject").eq("id", request.email_id).execute()
                if email_res.data:
                    email = email_res.data[0]
            except Exception:
                pass
        
        # If not in database, try mock_inbox.json
        if not email:
            try:
                with open("mock_inbox.json", "r") as f:
                    mock_emails = json.load(f)
                mock_email = next((e for e in mock_emails if str(e.get("id")) == str(request.email_id)), None)
                if mock_email:
                    email = {
                        "sender": mock_email.get("sender"),
                        "subject": mock_email.get("subject"),
                        "body": mock_email.get("body")
                    }
            except FileNotFoundError:
                pass
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # 2. Fetch System Prompt (Try 'general_agent', fallback to generic)
        system_instruction = "You are a helpful AI assistant. You are analyzing the following email. Answer the user's questions based on the email content."
        
        if supabase:
            try:
                prompt_res = supabase.table("prompts").select("content").eq("prompt_type", "general_agent").execute()
                if prompt_res.data:
                    system_instruction = prompt_res.data[0]['content']
            except Exception:
                pass

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
        if request.language and request.language.lower() not in ["en", "english"]:
            user_query = f"Please respond in {request.language}.\n\nUser Query: {request.user_query}"
        else:
            user_query = request.user_query

        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_query}
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
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")

    try:
        # 1. Fetch Email (try database first, then mock data)
        email = None
        email_from_db = False
        
        # Try database only if email_id looks like a UUID
        if supabase and len(str(request.email_id)) > 10 and '-' in str(request.email_id):
            try:
                email_res = supabase.table("emails").select("body, sender, subject").eq("id", request.email_id).execute()
                if email_res.data:
                    email = email_res.data[0]
                    email_from_db = True
            except Exception:
                pass  # Not a valid UUID, skip database
        
        # If not in database, try mock_inbox.json
        if not email:
            try:
                with open("mock_inbox.json", "r") as f:
                    mock_emails = json.load(f)
                mock_email = next((e for e in mock_emails if str(e.get("id")) == str(request.email_id)), None)
                if mock_email:
                    email = {
                        "sender": mock_email.get("sender"),
                        "subject": mock_email.get("subject"),
                        "body": mock_email.get("body")
                    }
            except FileNotFoundError:
                pass
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        # 2. Fetch 'auto_reply' Prompt
        system_instruction = "Draft a professional reply to this email."
        if supabase:
            prompt_res = supabase.table("prompts").select("content").eq("prompt_type", "auto_reply").execute()
            if prompt_res.data:
                system_instruction = prompt_res.data[0]['content']

        # 3. Call OpenAI
        language_instruction = "" if not request.language or request.language.lower() in ["en", "english"] else f"Write the subject and body in {request.language}."
        system_prompt = f"""
        {system_instruction}
        {language_instruction}
        
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

        # 4. Insert into drafts table (only if email was from database)
        draft_data = {
            "draft_subject": draft_json.get("draft_subject"),
            "draft_body": draft_json.get("draft_body")
        }
        
        if email_from_db and supabase:
            draft_data["email_id"] = request.email_id
            insert_res = supabase.table("drafts").insert(draft_data).execute()
            return {"message": "Draft generated successfully", "draft": insert_res.data[0]}
        else:
            # Return draft without saving for mock emails
            return {"message": "Draft generated successfully", "draft": draft_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Gmail OAuth & Sync Endpoints
# =============================================================================

# Note: You need to create the user_tokens table in Supabase:
# CREATE TABLE IF NOT EXISTS user_tokens (
#     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
#     user_email TEXT UNIQUE NOT NULL,
#     token_data JSONB NOT NULL,
#     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
#     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
# );

@app.get("/auth/gmail")
async def auth_gmail():
    """
    Initiates Gmail OAuth flow. Returns authorization URL for user to visit.
    """
    try:
        authorization_url, state = gmail_sync.get_authorization_url()
        return {
            "authorization_url": authorization_url,
            "state": state,
            "message": "Visit the authorization_url to grant Gmail access"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/gmail/callback")
async def auth_gmail_callback(code: str, state: str):
    """
    Handles OAuth callback from Google. Exchanges code for tokens and stores them.
    """
    try:
        # Exchange authorization code for tokens
        token_data = gmail_sync.exchange_code_for_token(code, state)
        
        # Get user's email address
        service = gmail_sync.build_service(token_data)
        user_email = gmail_sync.get_user_email(service)
        
        # Store tokens in database (upsert)
        token_record = {
            "user_email": user_email,
            "token_data": token_data,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Try to update existing record, if not exists then insert
        existing = supabase.table("user_tokens").select("*").eq("user_email", user_email).execute()
        
        if existing.data:
            supabase.table("user_tokens").update(token_record).eq("user_email", user_email).execute()
        else:
            supabase.table("user_tokens").insert(token_record).execute()
        
        # Return HTML that closes popup and notifies parent window
        html_content = f"""
        <html>
        <head><title>Gmail Connected</title></head>
        <body>
            <h2>✅ Gmail Connected Successfully!</h2>
            <p>You can close this window.</p>
            <script>
                // Notify parent window
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'gmail_connected',
                        user_email: '{user_email}'
                    }}, '*');
                    setTimeout(() => window.close(), 1000);
                }} else {{
                    // If not popup, redirect to main page
                    setTimeout(() => {{
                        window.location.href = '/';
                    }}, 2000);
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SyncGmailRequest(BaseModel):
    user_email: str
    max_results: Optional[int] = 50


@app.post("/sync/gmail")
async def sync_gmail(request: SyncGmailRequest):
    """
    Fetches emails from Gmail using stored OAuth tokens and runs AI analysis.
    """
    try:
        # 1. Retrieve stored tokens for this user
        token_result = supabase.table("user_tokens").select("token_data").eq("user_email", request.user_email).execute()
        
        if not token_result.data:
            raise HTTPException(status_code=404, detail="No Gmail tokens found for this user. Please authenticate first.")
        
        token_data = token_result.data[0]["token_data"]
        
        # 2. Fetch emails from Gmail
        emails = gmail_sync.fetch_emails(token_data, max_results=request.max_results)
        
        if not emails:
            return {"message": "No new emails to sync", "synced_count": 0}
        
        # 3. Insert emails into database and run AI analysis
        synced_count = 0
        analyzed_count = 0
        
        for email_data in emails:
            # Check if email already exists (by message_id)
            existing = supabase.table("emails").select("id").eq("message_id", email_data.get("message_id")).execute()
            
            if existing.data:
                continue  # Skip if already synced
            
            # Insert email
            email_record = {
                "from_address": email_data.get("from"),
                "to_address": email_data.get("to"),
                "subject": email_data.get("subject"),
                "body": email_data.get("body"),
                "received_at": email_data.get("date"),
                "message_id": email_data.get("message_id"),
                "has_attachments": len(email_data.get("attachments", [])) > 0,
                "attachment_names": [att.get("filename") for att in email_data.get("attachments", [])]
            }
            
            insert_result = supabase.table("emails").insert(email_record).execute()
            email_id = insert_result.data[0]["id"]
            synced_count += 1
            
            # 4. Run AI analysis on the email
            try:
                # Get all prompts
                prompts_result = supabase.table("prompts").select("*").eq("is_active", True).execute()
                prompts = prompts_result.data
                
                if not prompts:
                    continue
                
                # Prepare email content for analysis
                email_content = f"""
                From: {email_data.get('from')}
                Subject: {email_data.get('subject')}
                Body: {email_data.get('body')}
                """
                
                # Categorization analysis
                categorization_prompt = next((p for p in prompts if p["type"] == "categorization"), None)
                if categorization_prompt:
                    cat_completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": categorization_prompt["system_prompt"]},
                            {"role": "user", "content": email_content}
                        ]
                    )
                    category = cat_completion.choices[0].message.content
                else:
                    category = "Uncategorized"
                
                # Task extraction analysis
                task_prompt = next((p for p in prompts if p["type"] == "task_extraction"), None)
                tasks = []
                if task_prompt:
                    task_completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": task_prompt["system_prompt"]},
                            {"role": "user", "content": email_content}
                        ]
                    )
                    task_content = task_completion.choices[0].message.content
                    try:
                        task_data = json.loads(task_content)
                        tasks = task_data.get("tasks", [])
                    except:
                        tasks = []
                
                # Store analysis
                analysis_record = {
                    "email_id": email_id,
                    "category": category,
                    "extracted_tasks": tasks,
                    "has_tasks": len(tasks) > 0,
                    "all_tasks_completed": False
                }
                
                supabase.table("email_analysis").insert(analysis_record).execute()
                analyzed_count += 1
                
            except Exception as analysis_error:
                print(f"Analysis failed for email {email_id}: {str(analysis_error)}")
                continue
        
        return {
            "message": "Gmail sync completed",
            "synced_count": synced_count,
            "analyzed_count": analyzed_count
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AWS Lambda Handler
# =============================================================================

from mangum import Mangum
handler = Mangum(app)
