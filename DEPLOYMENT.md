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

#### Step 2: Deploy on Vercel (Frontend Only)

**Option A: Via Vercel Dashboard**
1. Go to https://vercel.com/dashboard
2. Click "Add New" → "Project"
3. Import your GitHub repository
4. Set Build Settings:
   - **Framework Preset**: Create React App (or React)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`
   - **Install Command**: `npm install`
   *(Note: Do not install Python requirements on Vercel. Vercel Serverless Functions have a 250MB size limit which PyTorch exceeds. Deploy the backend separately on Render.)*
5. Add Environment Variables:
   - `REACT_APP_API_URL`: Will be your Render API URL (e.g., `https://your-backend.onrender.com`)
6. Click "Deploy"

**Option B: Via Vercel CLI**
```bash
npm install -g vercel
cd frontend
vercel
# Follow the interactive prompts
```

#### Step 3: Configure API Backend (Render Recommended)
Due to the large size of AI models (PyTorch + Librosa), the backend should be deployed to a container service like Render.

1. Go to https://render.com
2. Create a new "Web Service"
3. Connect your GitHub repository
4. Setup configuration:
   - **Environment**: Docker
   - **Branch**: main
5. Click "Deploy Web Service"
*(Render will automatically build and deploy using the `Dockerfile` in the root directory)*

### Deployment Architecture

```
Frontend: Vercel Edge Network (React App)
Backend: Vercel Functions or Heroku (FastAPI)
Models: Stored with project or in CDN
```

### Deploy to Netlify (Frontend) + Render (Backend)

**1. Backend (Render):**
Since the backend uses heavy AI models (PyTorch), deploy it using Docker to Render:
1. Go to https://render.com and create a new **Web Service**.
2. Connect your GitHub repository.
3. Select **Docker** as the environment.
4. Click **Deploy**. Render will use the provided `Dockerfile`.
5. Once deployed, copy your API URL (e.g., `https://reefvoice-backend.onrender.com`).

**2. Frontend (Netlify):**
1. Go to https://app.netlify.com and click **Add new site** → **Import an existing project**.
2. Connect your GitHub repository.
3. Netlify will automatically read the `netlify.toml` file we provided. Ensure the settings look like this:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/build`
4. Click **Add environment variables** and add:
   - Key: `REACT_APP_API_URL`
   - Value: `<Your Render API URL from Step 1>`
5. Click **Deploy Site**.

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
