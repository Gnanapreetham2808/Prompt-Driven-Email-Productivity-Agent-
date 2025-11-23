-- Migration: Add attachments + starring + previous_category support
-- Run this against existing Supabase Postgres instance

ALTER TABLE emails
  ADD COLUMN IF NOT EXISTS is_starred BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]';

ALTER TABLE email_analysis
  ADD COLUMN IF NOT EXISTS previous_category TEXT;