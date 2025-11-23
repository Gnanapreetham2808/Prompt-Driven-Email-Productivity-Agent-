# 🚀 Deployment Guide

## Quick Deploy Options

### Option 1: Render (Easiest - Free Tier)

**Backend Deployment:**
1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repo
4. Settings:
   - **Name**: `email-agent-api`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Add your env vars (SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY)

**Frontend Deployment:**
1. Go to https://render.com
2. Click "New +" → "Static Site"
3. Connect your GitHub repo
4. Settings:
   - **Root Directory**: `frontend`
   - **Publish Directory**: `.`
5. After deploy, update `index.html`:
   ```javascript
   const API_URL = 'https://your-backend-url.onrender.com';
   ```

### Option 2: Vercel (Frontend) + Render (Backend)

**Frontend on Vercel:**
```bash
cd frontend
vercel deploy
```

**Backend on Render:** (Same as Option 1)

### Option 3: Railway (All-in-One)

1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Add two services:
   - **Backend**: Auto-detects Python, add env vars
   - **Frontend**: Static site from `frontend` folder

### Environment Variables (All Platforms)

```
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_KEY=your_anon_public_key
OPENAI_API_KEY=sk-your_key_here
```

## Pre-Deployment Checklist

- [ ] `.env` file NOT committed (check .gitignore)
- [ ] Database tables created in Supabase
- [ ] `/init-prompts` endpoint called once
- [ ] CORS origins updated in production
- [ ] Frontend API_URL points to deployed backend
- [ ] Test all features work with deployed URLs

## Production Optimizations

### 1. Update CORS for Production

In `backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.vercel.app",
        "http://localhost:8080"  # Keep for local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Add Health Check Endpoint

Already have `GET /` - perfect for monitoring!

### 3. Error Handling

Already implemented - HTTPException returns proper status codes.

## Cost Estimate (Free Tiers)

- **Render**: Free tier includes 750 hours/month
- **Vercel**: 100GB bandwidth/month free
- **Railway**: $5 credit/month free
- **Supabase**: 500MB database free
- **OpenAI**: Pay per use (~$0.002 per email)

**Estimated cost for demo**: $0-2/month

## Troubleshooting Deploy Issues

**CORS errors:**
- Update `allow_origins` in backend
- Ensure frontend uses HTTPS if backend uses HTTPS

**Database connection fails:**
- Verify env vars are set in hosting platform
- Check Supabase isn't in maintenance window

**Cold starts (Render free tier):**
- First request takes 30-60 seconds
- Add a "wakeup" endpoint that pings every 10 minutes

## Demo URL Structure

Once deployed:
- Backend: `https://email-agent-api.onrender.com`
- Frontend: `https://email-agent.vercel.app`
- Docs: `https://email-agent-api.onrender.com/docs` (FastAPI auto-generates!)

## Post-Deployment Testing

1. Open frontend URL
2. Go to "Agent Brain" → Verify prompts load
3. Click "Ingest Emails" → Verify 15 emails appear
4. Click an email → Test chat and draft features
5. Edit a prompt → Save → Re-ingest to verify change

---

**Your app is now live and accessible worldwide!** 🌍
