# Deployment Guide

## Phase 1: Push to GitHub
1. Create a new repository on GitHub (e.g., `research-ai-agent`).
2. Run the following commands in your terminal (replace `<YOUR_REPO_URL>` with the actual URL):
   ```bash
   git remote add origin <YOUR_REPO_URL>
   git branch -M main
   git push -u origin main
   ```

## Phase 2: Deploy Backend (Render)
1. Go to [Render.com](https://render.com) and sign up/login.
2. Click **"New +"** -> **"Web Service"**.
3. Connect your GitHub repository.
4. Use the following settings:
   - **Name:** `research-agent-backend`
   - **Root Directory:** `.` (leave default)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -w 4 -k uvicorn.workers.UvicornWorker api:app`
5. Scroll down to **"Environment Variables"** and add:
   - Key: `GOOGLE_API_KEY` | Value: (Your NEW Gemini API Key)
   - Key: `TAVILY_API_KEY` | Value: (Your Tavily API Key)
6. Click **"Create Web Service"**.
7. Wait for deployment. Copy the **Service URL** (e.g., `https://research-agent-backend.onrender.com`).

## Phase 3: Deploy Frontend (Vercel)
1. Go to [Vercel.com](https://vercel.com) and sign up/login.
2. Click **"Add New..."** -> **"Project"**.
3. Import the same GitHub repository.
4. Configure the project:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Click "Edit" and select `frontend`.
5. Open **"Environment Variables"** and add:
   - Key: `NEXT_PUBLIC_API_URL` | Value: (Paste your Render Backend URL here, e.g., `https://research-agent-backend.onrender.com`)
     *IMPORTANT: Do not add a trailing slash `/` at the end.*
6. Click **"Deploy"**.

## Phase 4: Final Test
1. Open your Vercel URL.
2. Type "Hello" to test the connection.
