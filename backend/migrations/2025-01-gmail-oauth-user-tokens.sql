-- Migration: Add user_tokens table for Gmail OAuth
-- Date: 2025-01-XX
-- Description: Stores OAuth tokens (access_token, refresh_token) for Gmail users

CREATE TABLE IF NOT EXISTS user_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT UNIQUE NOT NULL,
    token_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on user_email for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_tokens_email ON user_tokens(user_email);

-- Add comment to table
COMMENT ON TABLE user_tokens IS 'Stores OAuth tokens for Gmail integration. token_data contains access_token, refresh_token, token_uri, client_id, client_secret, scopes, and expiry.';
