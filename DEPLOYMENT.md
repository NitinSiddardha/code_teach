# Deployment Guide

## What Changed
This update includes:
- **New Frontend**: Multi-screen onboarding, better UI/UX, clear message styling
- **Assessment Flow**: Quick assessment before learning starts
- **Topic Explanations**: Context for each topic is displayed
- **Optimized Prompts**: Reduced token usage, less hallucination
- **Better Messages**: Visual distinction between teacher and student messages

## Deploying to Render (Button-Click Steps)

### First Time Setup (if you haven't deployed yet)
1. Push your code to GitHub
2. Go to https://render.com
3. Click "New +" > "Web Service"
4. Connect your GitHub account and select this repo
5. Set these values:
   - **Name**: code-teach
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT wsgi:app`
6. Add Environment Variable:
   - **Key**: `GOOGLE_API_KEY`
   - **Value**: (your Google API key)
7. Click "Create Web Service"

### Updating Your Existing Deployment
1. Commit and push your changes to GitHub:
   ```bash
   git add .
   git commit -m "Improved frontend and token optimization"
   git push
   ```
2. Go to your Render dashboard
3. Select your service (code-teach)
4. Click "Deployments" on the top right
5. The new deployment should start automatically
6. Wait for the build to complete (2-3 minutes)
7. Once deployed, visit your app URL

## What You Don't Need to Change
- The `render.yaml`, `Procfile`, and environment variables are already configured
- The Python dependencies are already in `requirements.txt`
- No manual build or configuration steps needed

## Testing Your Deployment
Once deployed, visit your Render URL and:
1. You should see the landing page
2. Click "Get Started"
3. Select a topic and level
4. Answer the assessment questions
5. Start the learning session

## Token Optimization
The prompts are now optimized to:
- Return max 2-3 sentences per response (was unlimited)
- Avoid long explanations unless requested
- Focus on execution results rather than code critique
- Prevent hallucination through specific constraints

## Troubleshooting
If the deployment fails:
1. Check the Render logs (click "Logs" in the dashboard)
2. Common issues:
   - Missing `GOOGLE_API_KEY` environment variable (add it)
   - Python dependency errors (shouldn't happen, but check `requirements.txt`)
   - Port binding (should be automatic via `$PORT`)

## Quick Reference
- **App starts on**: `https://<your-service-name>.onrender.com`
- **Health check**: `https://<your-service-name>.onrender.com/health`
- **API endpoints**:
  - `/api/session/start` (POST)
  - `/api/session/submit` (POST)
  - `/api/session/signal` (POST)
  - `/api/session/end` (POST)
