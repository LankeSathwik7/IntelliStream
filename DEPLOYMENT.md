# IntelliStream Deployment Guide

Deploy the backend to HuggingFace Spaces (free Docker hosting) and frontend to Cloudflare Pages (free static hosting).

## Prerequisites

Before deploying, ensure you have:

1. **Supabase Project** (free tier)
   - Create at https://supabase.com
   - Get `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

2. **Groq API Key** (free tier)
   - Get at https://console.groq.com
   - Get `GROQ_API_KEY`

3. **Voyage AI API Key** (free tier)
   - Get at https://www.voyageai.com
   - Get `VOYAGE_API_KEY`

4. **Upstash Redis** (optional, free tier)
   - Create at https://upstash.com
   - Get `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`

---

## Backend: HuggingFace Spaces

### Step 1: Create a HuggingFace Account

1. Go to https://huggingface.co and sign up
2. Create a new Space: https://huggingface.co/new-space
3. Choose:
   - **Space name**: `intellistream-api`
   - **SDK**: Docker
   - **Hardware**: CPU Basic (free)

### Step 2: Configure Secrets

In your Space settings, add these secrets:

```
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
GROQ_API_KEY=your_groq_key
VOYAGE_API_KEY=your_voyage_key
UPSTASH_REDIS_REST_URL=your_redis_url (optional)
UPSTASH_REDIS_REST_TOKEN=your_redis_token (optional)
ENVIRONMENT=production
DEBUG=false
```

### Step 3: Deploy

**Option A: Git Push (Recommended)**

```bash
cd backend
git init
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/intellistream-api
git add .
git commit -m "Initial deployment"
git push space main
```

**Option B: Upload Files**

1. Go to your Space's Files tab
2. Upload all files from the `backend/` directory
3. The Space will automatically build and deploy

### Step 4: Verify

Your API will be available at:
```
https://YOUR_USERNAME-intellistream-api.hf.space
```

Test with:
```bash
curl https://YOUR_USERNAME-intellistream-api.hf.space/health
```

---

## Frontend: Cloudflare Pages

### Step 1: Create Cloudflare Account

1. Go to https://dash.cloudflare.com and sign up
2. Navigate to Workers & Pages > Create application > Pages

### Step 2: Connect Repository

**Option A: Git Integration**

1. Connect your GitHub/GitLab repository
2. Select the repository containing your frontend code
3. Configure build settings:
   - **Framework preset**: Next.js (Static HTML Export)
   - **Build command**: `npm run build`
   - **Build output directory**: `out`
   - **Root directory**: `frontend`

**Option B: Direct Upload**

1. Build locally:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
2. Upload the `out/` folder to Cloudflare Pages

### Step 3: Configure Environment Variables

In your project settings, add:

```
NEXT_PUBLIC_API_URL=https://YOUR_USERNAME-intellistream-api.hf.space
```

### Step 4: Deploy

Click "Save and Deploy". Your frontend will be available at:
```
https://intellistream.pages.dev
```

Or use a custom domain in the Custom Domains tab.

---

## Post-Deployment Checklist

1. **Test Health Endpoint**
   ```bash
   curl https://YOUR_API_URL/health
   ```

2. **Test Chat Endpoint**
   ```bash
   curl -X POST https://YOUR_API_URL/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello", "thread_id": "test"}'
   ```

3. **Update CORS** (if needed)
   Edit `backend/app/main.py` to restrict origins:
   ```python
   allow_origins=["https://intellistream.pages.dev"],
   ```

4. **Update Frontend URL** in backend config:
   ```
   FRONTEND_URL=https://intellistream.pages.dev
   ```

---

## Troubleshooting

### HuggingFace Spaces

- **Build fails**: Check `requirements.txt` for version conflicts
- **Memory issues**: Upgrade to paid tier or optimize code
- **Slow cold starts**: Expected on free tier, first request may take 30-60s

### Cloudflare Pages

- **Build fails**: Ensure `output: "export"` in `next.config.ts`
- **API calls fail**: Check CORS and `NEXT_PUBLIC_API_URL`
- **404 on routes**: Verify `trailingSlash: true` in config

---

## Cost Summary

| Service | Free Tier Limits |
|---------|------------------|
| HuggingFace Spaces | 2 vCPU, 16GB RAM, sleeps after inactivity |
| Cloudflare Pages | 500 builds/month, unlimited requests |
| Supabase | 500MB DB, 1GB storage, 50k monthly active users |
| Groq | Rate limited, no fixed quota |
| Voyage AI | 200M tokens/month |
| Upstash Redis | 10k commands/day |
