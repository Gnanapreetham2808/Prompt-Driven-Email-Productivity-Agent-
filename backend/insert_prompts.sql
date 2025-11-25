-- Insert default prompts for email analysis
-- Run this in Supabase SQL Editor

-- Delete existing prompts first
DELETE FROM prompts WHERE prompt_type IN ('categorization', 'action_item', 'auto_reply');

-- Insert categorization prompt
INSERT INTO prompts (prompt_type, content)
VALUES (
    'categorization',
    'Analyze this email and categorize it into ONE of these categories: 
    - "Urgent Task" (requires immediate action)
    - "Meeting" (meeting invitations, calendar items)
    - "Project Update" (status updates, sprint reviews)
    - "Newsletter" (marketing emails, digests, weekly roundups)
    - "Notification" (automated system notifications, alerts)
    - "Client Communication" (emails from clients/partners)
    - "Spam" (promotional, suspicious, irrelevant)
    - "General" (everything else)
    
    Choose the MOST SPECIFIC category that applies.'
);

-- Insert action item extraction prompt
INSERT INTO prompts (prompt_type, content)
VALUES (
    'action_item',
    'Extract actionable tasks from this email. For each task, identify:
    - The specific action to be taken
    - Any deadline or due date mentioned (if any)
    
    Only return tasks that require the recipient to DO something.
    Ignore informational content or passive updates.
    
    Return empty list if no action items exist.'
);

-- Insert auto reply prompt
INSERT INTO prompts (prompt_type, content)
VALUES (
    'auto_reply',
    'Draft a professional, concise reply to this email. 
    
    Guidelines:
    - Be polite and professional
    - Address the main points from the original email
    - Keep it brief (2-3 paragraphs maximum)
    - Use appropriate tone based on sender and context
    - End with a clear call-to-action or next steps if needed
    - Do not make up information - only respond based on the email content'
);

-- Verify prompts were inserted
SELECT * FROM prompts ORDER BY created_at DESC;
