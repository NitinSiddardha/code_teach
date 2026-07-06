# For Render Deployment - Quick Start

## You Only Need to Do This Once (Already Done)
The app is configured for Render. Here's what's already set up:

- `render.yaml` - Render reads this automatically
- `Procfile` - Backup configuration (also on Render)
- `wsgi.py` - App entry point for Gunicorn
- `app/web/routes.py` - All API endpoints

## To Deploy Your Changes

### Step 1: Commit and Push
```bash
git add .
git commit -m "Frontend redesign and optimization"
git push origin main
```

### Step 2: Render Redeploys Automatically
- Render watches your GitHub repo
- When you push, Render automatically builds and deploys
- Takes about 2-3 minutes
- You can watch in the Render dashboard

### Step 3: Done!
Visit your app URL (something like `https://code-teach.onrender.com`)

## If Something Goes Wrong
1. Go to your Render dashboard
2. Click your service
3. Click "Logs" tab
4. Look for error messages
5. Common issues:
   - Missing `GOOGLE_API_KEY` environment variable
   - Python syntax error (but we checked this)
   - Dependency not in `requirements.txt` (unlikely)

## Your Render Environment Already Has
```
PYTHON_VERSION: 3.11.9
Build Command: pip install -r requirements.txt
Start Command: gunicorn --bind 0.0.0.0:$PORT wsgi:app
Health Check: /health
```

## No Additional Configuration Needed
You don't need to:
- Change any Render settings
- Edit `render.yaml` (unless you want to)
- Manually run build commands
- Configure port or host
- Set up a database (SQLite is local)

## Render Dashboard Tips
- **Deployments**: See all past deployments
- **Logs**: Real-time logs while app is running
- **Metrics**: CPU, memory, network usage
- **Environment**: Where you add `GOOGLE_API_KEY`
- **Settings**: Service name, region, etc.

## Your App URLs
- **Main URL**: `https://<service-name>.onrender.com/`
- **Health Check**: `https://<service-name>.onrender.com/health`
- **API Endpoints**:
  - `POST https://<service-name>.onrender.com/api/session/start`
  - `POST https://<service-name>.onrender.com/api/session/submit`
  - `POST https://<service-name>.onrender.com/api/session/signal`
  - `POST https://<service-name>.onrender.com/api/session/end`

## That's Literally It
Push code → Render builds → App deploys → Done

No clicking around, no manual configuration, no mystery steps.
