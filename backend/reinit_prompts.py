#!/usr/bin/env python3
"""
Script to reinitialize prompts in Supabase database.
Deletes all existing prompts and inserts the 3 default ones.
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL or SUPABASE_KEY not found in .env file")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Default prompts
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

try:
    # Delete all existing prompts
    print("🗑️  Deleting existing prompts...")
    supabase.table("prompts").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    
    # Insert new prompts
    print("📝 Inserting 3 default prompts...")
    result = supabase.table("prompts").insert(DEFAULT_PROMPTS).execute()
    
    print(f"✅ Successfully initialized {len(result.data)} prompts:")
    for prompt in result.data:
        content_preview = prompt['content'][:60].replace('\n', ' ')
        print(f"   - {prompt['prompt_type']}: {content_preview}...")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
