# ReefVoice Deployment Guide

## Quick Deployment Steps

### Prerequisites
- Vercel account (https://vercel.com)
- GitHub account (project pushed to GitHub)
- Node.js and npm installed locally

### Deploy to Vercel (Recommended)

#### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/reefvoice.git
git push -u origin main
```

#### Step 2: Deploy on Vercel

**Option A: Via Vercel Dashboard**
1. Go to https://vercel.com/dashboard
2. Click "Add New" → "Project"
3. Import your GitHub repository
4. Set Build Settings:
   - **Framework Preset**: React
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Output Directory**: `frontend/build`
   - **Install Command**: `npm install && pip install -r requirements.txt`
5. Add Environment Variables:
   - `REACT_APP_API_URL`: Will be your Vercel API URL
6. Click "Deploy"

**Option B: Via Vercel CLI**
```bash
npm install -g vercel
vercel
# Follow the interactive prompts
```

#### Step 3: Configure API Routes
In your Vercel project settings, ensure the API is routed correctly:
- Set the Python version to 3.11
- Add API routes mapping for `/api/*` endpoints

### Deployment Architecture

```
Frontend: Vercel Edge Network (React App)
Backend: Vercel Functions or Heroku (FastAPI)
Models: Stored with project or in CDN
```

### Alternative: Deploy to Heroku + Netlify

**Backend (Heroku):**
```bash
heroku create reefvoice-api
heroku config:set BUILDPACK_URL=https://github.com/heroku/heroku-buildpack-python.git
git push heroku main
```

**Frontend (Netlify):**
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=frontend/build
```

### Environment Variables to Set

Create `.env.production` for frontend:
```
REACT_APP_API_URL=https://your-api-domain.com
```

### Post-Deployment

1. Test the API endpoint: `https://your-domain.vercel.app/api/reefs`
2. Test the frontend: `https://your-domain.vercel.app/`
3. Monitor logs in Vercel dashboard

### Troubleshooting

- **Model loading issues**: Ensure torch and dependencies are in requirements.txt
- **CORS errors**: Check FastAPI CORS middleware is properly configured
- **Build timeouts**: Increase build timeout in Vercel settings or optimize dependencies

### Monitoring

- Vercel Analytics: Track real-time performance
- Function logs: View in Vercel dashboard
- Error tracking: Configure Sentry for production errors

---

**Your published site will be available at:** `https://your-project-name.vercel.app/`
