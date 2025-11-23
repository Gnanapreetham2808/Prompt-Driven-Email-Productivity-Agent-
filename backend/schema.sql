-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: prompts
-- Stores system prompts used for categorizing emails and generating replies.
CREATE TABLE IF NOT EXISTS prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_type TEXT NOT NULL, -- e.g., 'categorization', 'reply_generation'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: emails
-- Stores ingested emails.
CREATE TABLE IF NOT EXISTS emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender TEXT NOT NULL,
    subject TEXT,
    body TEXT,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_read BOOLEAN DEFAULT FALSE,
    is_starred BOOLEAN DEFAULT FALSE,
    attachments JSONB DEFAULT '[]'
);

-- Table: email_analysis
-- Stores the analysis result from the LLM (category, tasks).
CREATE TABLE IF NOT EXISTS email_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    category TEXT,
    previous_category TEXT,
    extracted_tasks JSONB, -- Stores tasks as a JSON array/object
    analysis_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: drafts
-- Stores generated draft replies.
CREATE TABLE IF NOT EXISTS drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    draft_subject TEXT,
    draft_body TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
