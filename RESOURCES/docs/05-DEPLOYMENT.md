# Deployment

## Option A: Railway (Recommended — Free Tier)

Railway runs the backend 24/7. The frontend is served by FastAPI at `/app`.

### Steps

1. **Create a GitHub repo** with the `backend/` folder contents at the root
2. **Connect Railway** to the repo: https://railway.app
3. **Deploy** — Railway auto-detects Python and runs `uvicorn main:app`
4. **Set environment variable:** `DB_PATH=/data/jobhunter.db` (persistent disk)
5. **Add a volume** at `/data` so SQLite persists across deploys
6. **Build command** (if needed): `pip install -r requirements.txt && playwright install chromium`

### `Procfile` (already in backend/)
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### `railway.json` (already in backend/)
```json
{
  "build": {"builder": "nixpacks"},
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/health"
  }
}
```

### After Deploy

1. Open the Railway URL (e.g., `https://jobhunter.up.railway.app`)
2. Go to Settings tab
3. Fill in candidate details, API keys, resume
4. Done — it runs daily at 8 AM

---

## Option B: Render (Alternative Free Tier)

1. Create a GitHub repo with `backend/` at root
2. Connect to https://render.com
3. New → Web Service → Select repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add a persistent disk at `/data` for SQLite

---

## Option C: Local (Testing)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000` for the dashboard.
Open `http://localhost:8000/docs` for API docs.

---

## Frontend-Only Deploy (Optional)

If you want the frontend on a separate URL (e.g., Vercel):

1. Deploy `frontend/index.html` to Vercel
2. Edit the `API` constant in the HTML:
   ```javascript
   const API = 'https://jobhunter.up.railway.app';  // Your Railway URL
   ```
3. Make sure Railway has CORS enabled (it does — `allow_origins=["*"]`)

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `DB_PATH` | `./jobhunter.db` | SQLite database file path |
| `PORT` | `8000` | Server port (set by Railway automatically) |

---

## Post-Deploy Checklist

- [ ] `/api/health` returns `{"status": "ok"}`
- [ ] Dashboard loads at the root URL
- [ ] Settings form saves correctly
- [ ] "Scrape Now" returns results
- [ ] Schedule shows next run time
- [ ] SQLite persists across deploys (volume mounted)
