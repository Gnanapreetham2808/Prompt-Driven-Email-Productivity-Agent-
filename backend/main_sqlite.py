import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from openai import OpenAI
from dotenv import load_dotenv
from models import Base, Prompt, Email, EmailAnalysis, Draft
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = "sqlite+aiosqlite:///./email_agent.db"

# Initialize SQLite Database
engine = create_engine("sqlite:///./email_agent.db", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize OpenAI Client
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not set.")
    openai_client = None
else:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Prompt-Driven Email Productivity Agent")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
async def init_prompts(db: Session = Depends(get_db)):
    """
    Checks if the prompts table is empty, and if so, inserts default prompts.
    """
    try:
        count = db.query(func.count(Prompt.id)).scalar()
        
        if count > 0:
            return {"message": "Prompts table is not empty. Initialization skipped."}

        # Insert default prompts
        for prompt_data in DEFAULT_PROMPTS:
            prompt = Prompt(**prompt_data)
            db.add(prompt)
        
        db.commit()
        
        return {"message": "Default prompts initialized successfully."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/")
async def root():
    return {"message": "API is running with SQLite database"}

@app.post("/ingest")
async def ingest_emails(db: Session = Depends(get_db)):
    """
    Ingests emails from mock_inbox.json, analyzes them using OpenAI,
    and stores the results in SQLite.
    """
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")

    try:
        # Load mock emails
        try:
            with open("mock_inbox.json", "r") as f:
                emails = json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="mock_inbox.json not found")

        results = []
        
        for email_data in emails:
            # 1. Insert email into database
            email = Email(
                sender=email_data["sender"],
                subject=email_data["subject"],
                body=email_data["body"],
                received_at=datetime.fromisoformat(email_data["timestamp"].replace('Z', '+00:00')),
                is_read=False
            )
            db.add(email)
            db.flush()  # Get the ID without committing

            # 2. Fetch prompts
            cat_prompt = db.query(Prompt).filter(Prompt.prompt_type == "categorization").first()
            action_prompt = db.query(Prompt).filter(Prompt.prompt_type == "action_item").first()
            
            cat_content = cat_prompt.content if cat_prompt else "Categorize this email."
            action_content = action_prompt.content if action_prompt else "Extract tasks."

            # 3. Analyze with OpenAI
            system_prompt = f"""
            You are an email analysis engine.
            
            Task 1 (Categorization): {cat_content}
            Task 2 (Action Items): {action_content}
            
            Output Format: Return a valid JSON object with exactly these keys:
            - "category": string (e.g., "Meeting", "Newsletter", "Spam", "Task", "Project Update")
            - "extracted_tasks": list of objects, where each object has "task" (string) and "deadline" (string or null).
            """
            
            try:
                completion = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": email_data["body"]}
                    ],
                    response_format={"type": "json_object"}
                )
                
                analysis_content = completion.choices[0].message.content
                analysis_json = json.loads(analysis_content)
                
                # 4. Insert analysis
                analysis = EmailAnalysis(
                    email_id=email.id,
                    category=analysis_json.get("category"),
                    extracted_tasks=analysis_json.get("extracted_tasks")
                )
                db.add(analysis)
                results.append({"email_id": email.id, "status": "analyzed"})
                
            except Exception as ai_error:
                print(f"AI Analysis failed for email {email.id}: {ai_error}")
                results.append({"email_id": email.id, "status": "ingested_only", "error": str(ai_error)})

        db.commit()
        return {"message": "Ingestion process completed", "processed_count": len(results), "details": results}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.get("/prompts")
async def get_prompts(db: Session = Depends(get_db)):
    """
    Fetches all system prompts from the database.
    """
    try:
        prompts = db.query(Prompt).order_by(Prompt.created_at).all()
        return [{"id": p.id, "prompt_type": p.prompt_type, "content": p.content, "created_at": p.created_at.isoformat()} for p in prompts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, update: PromptContentUpdate, db: Session = Depends(get_db)):
    """
    Updates a specific prompt's content.
    """
    try:
        prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        prompt.content = update.content
        db.commit()
        
        return {"id": prompt.id, "prompt_type": prompt.prompt_type, "content": prompt.content}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails")
async def get_emails(db: Session = Depends(get_db)):
    """
    Fetches all emails with their analysis.
    """
    try:
        emails = db.query(Email).order_by(Email.received_at.desc()).all()
        result = []
        
        for email in emails:
            email_dict = {
                "id": email.id,
                "sender": email.sender,
                "subject": email.subject,
                "body": email.body,
                "received_at": email.received_at.isoformat(),
                "is_read": email.is_read,
                "email_analysis": []
            }
            
            if email.analysis:
                for analysis in email.analysis:
                    email_dict["email_analysis"].append({
                        "category": analysis.category,
                        "extracted_tasks": analysis.extracted_tasks
                    })
            
            result.append(email_dict)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/chat")
async def agent_chat(request: AgentChatRequest, db: Session = Depends(get_db)):
    """
    Chat with the agent about a specific email.
    """
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")

    try:
        email = db.query(Email).filter(Email.id == request.email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Fetch System Prompt
        prompt = db.query(Prompt).filter(Prompt.prompt_type == "general_agent").first()
        
        if prompt:
            system_instruction = prompt.content
        else:
            system_instruction = "You are a helpful AI assistant. You are analyzing the following email. Answer the user's questions based on the email content."

        system_message = f"""
        {system_instruction}

        --- EMAIL CONTEXT ---
        From: {email.sender}
        Subject: {email.subject}
        Body:
        {email.body}
        ---------------------
        """

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
async def generate_draft(request: DraftRequest, db: Session = Depends(get_db)):
    """
    Generates a draft reply for an email and saves it to the database.
    """
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")

    try:
        email = db.query(Email).filter(Email.id == request.email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        # Fetch 'auto_reply' Prompt
        prompt = db.query(Prompt).filter(Prompt.prompt_type == "auto_reply").first()
        system_instruction = prompt.content if prompt else "Draft a professional reply to this email."

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
                {"role": "user", "content": f"From: {email.sender}\nSubject: {email.subject}\nBody:\n{email.body}"}
            ],
            response_format={"type": "json_object"}
        )

        draft_content = completion.choices[0].message.content
        draft_json = json.loads(draft_content)

        # Insert into drafts table
        draft = Draft(
            email_id=request.email_id,
            draft_subject=draft_json.get("draft_subject"),
            draft_body=draft_json.get("draft_body")
        )
        db.add(draft)
        db.commit()
        
        return {
            "message": "Draft generated successfully",
            "draft": {
                "id": draft.id,
                "email_id": draft.email_id,
                "draft_subject": draft.draft_subject,
                "draft_body": draft.draft_body,
                "created_at": draft.created_at.isoformat()
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
