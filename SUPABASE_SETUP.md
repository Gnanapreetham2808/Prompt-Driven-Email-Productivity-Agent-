# Supabase Setup Instructions

## Step 1: Create Supabase Account
1. Go to https://supabase.com
2. Sign up for a free account
3. Click "New Project"
4. Choose an organization (or create one)
5. Fill in project details:
   - Name: `email-agent`
   - Database Password: (save this somewhere secure)
   - Region: Choose closest to you
6. Click "Create new project" (takes ~2 minutes)

## Step 2: Get API Credentials
1. Once project is created, go to **Project Settings** (gear icon)
2. Click **API** in the left sidebar
3. Copy these two values:
   - **Project URL** → This is your `SUPABASE_URL`
   - **anon public** key → This is your `SUPABASE_KEY`

## Step 3: Update .env File
Open `backend/.env` and paste your values:
```
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
OPENAI_API_KEY=sk-...
```

## Step 4: Run SQL Schema
1. In Supabase Dashboard, click **SQL Editor** (left sidebar)
2. Click **New Query**
3. Copy the contents of `backend/schema.sql`
4. Paste into the query editor
5. Click **Run** or press Ctrl+Enter

## Step 5: Install Dependencies & Run
```powershell
cd backend
..\venv\Scripts\pip install -r requirements.txt
..\venv\Scripts\uvicorn main:app --reload
```

## Step 6: Initialize Prompts
Open your browser to http://localhost:8080 and:
1. The backend should show no errors
2. Go to "Agent Brain" tab
3. Prompts should appear (or call `/init-prompts` endpoint first)

## Troubleshooting
- **"Invalid URL" error**: Check that SUPABASE_URL starts with `https://`
- **"Invalid API key" error**: Make sure you copied the **anon public** key, not the service_role key
- **Tables not found**: Run the SQL schema in Step 4
- **During Supabase maintenance**: Your app will still work, but you can't access the dashboard to create projects or run SQL

## Free Tier Limits
- 500MB database
- 2GB bandwidth/month
- Unlimited API requests
- Perfect for development and small production apps
