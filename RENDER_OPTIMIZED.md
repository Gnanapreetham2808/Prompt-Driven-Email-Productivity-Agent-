# Production Deployment Guide

## 🚀 Optimized Render Deployment

### Improvements Made:
1. ✅ **Faster Builds**: Separate `requirements-render.txt` with only essential dependencies
2. ✅ **Better Performance**: 2 workers, optimized timeout settings
3. ✅ **Auto API Detection**: Frontend automatically connects to production API
4. ✅ **Security Headers**: Added X-Frame-Options, X-Content-Type-Options
5. ✅ **Dual Service**: Separate backend API and frontend static site
6. ✅ **Health Checks**: Automatic health monitoring
7. ✅ **Auto Deploy**: Enabled for continuous deployment

### Quick Deploy Steps:

#### 1. Push to GitHub
```bash
git add .
git commit -m "Optimized Render deployment with dual services"
git push origin main
```

#### 2. Deploy to Render
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository: `Gnanapreetham2808/Prompt-Driven-Email-Productivity-Agent-`
4. Render will auto-detect `render.yaml`
5. Click **"Apply"**

#### 3. Configure Environment Variables
In Render Dashboard, add these for `email-agent-api`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
OPENAI_API_KEY=sk-your_openai_api_key
```

#### 4. Access Your App
- **Backend API**: `https://email-agent-api.onrender.com`
- **Frontend**: `https://email-agent-frontend.onrender.com`

### Architecture:

```
┌─────────────────────────────────────────┐
│  Frontend (Static Site)                 │
│  email-agent-frontend.onrender.com      │
│  - HTML/CSS/JS                          │
│  - Auto-detects API URL                 │
└──────────────┬──────────────────────────┘
               │
               │ HTTPS Requests
               ▼
┌─────────────────────────────────────────┐
│  Backend API (Web Service)              │
│  email-agent-api.onrender.com           │
│  - FastAPI + Uvicorn                    │
│  - 2 Workers                            │
│  - Health checks                        │
└──────────────┬──────────────────────────┘
               │
               ├──► Supabase (Database)
               ├──► OpenAI (AI Processing)
               └──► Gmail API (Email Sync)
```

### Features:
- ✅ 100 pre-categorized mock emails
- ✅ Gmail OAuth integration
- ✅ AI-powered email categorization
- ✅ Automated draft generation
- ✅ Star/filter functionality
- ✅ Agent Brain (prompt customization)
- ✅ Responsive UI

### Performance Optimizations:
1. **Minimal Dependencies**: `requirements-render.txt` (30 packages vs 282)
2. **Multiple Workers**: 2 Uvicorn workers for better concurrency
3. **Keep-Alive Timeout**: 65s for stable connections
4. **Static Caching**: 1-hour cache for frontend assets
5. **Auto-scaling**: Render handles traffic spikes

### Monitoring:
- Health endpoint: `https://email-agent-api.onrender.com/health`
- Logs: Available in Render dashboard
- Metrics: Response time, error rates, uptime

### Free Tier Limits:
- ⚠️ Spins down after 15 minutes of inactivity
- ⚠️ 750 hours/month (shared across services)
- ⚠️ 512 MB RAM per service
- ✅ Automatic HTTPS
- ✅ Custom domains supported

### Upgrade to Paid ($7/month per service):
- Always-on services (no spin-down)
- More RAM (1-16 GB)
- Better performance
- Priority support

### Troubleshooting:

**Build Failures:**
```bash
# Check requirements-render.txt has all dependencies
# View build logs in Render dashboard
```

**API Connection Issues:**
```javascript
// Frontend auto-detects API URL
// Check browser console for API_URL value
console.log('API URL:', API_URL);
```

**Environment Variables:**
```bash
# Verify in Render dashboard:
# Settings → Environment → Environment Variables
```

### Alternative: Deploy Backend Only
If you only want to deploy the backend:
1. Remove the `static` service from `render.yaml`
2. Keep only the `web` service
3. Host frontend elsewhere (GitHub Pages, Netlify, Vercel)

### Support:
- Render Docs: https://render.com/docs
- Status: https://status.render.com
- Community: https://community.render.com
