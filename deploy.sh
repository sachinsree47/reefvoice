#!/bin/bash
# ReefVoice Quick Deploy Script for Vercel

echo "🌊 ReefVoice Deployment Script"
echo "================================"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit"
    git branch -M main
fi

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "Installing Vercel CLI..."
    npm install -g vercel
fi

# Check if vercel is logged in
echo "Authenticating with Vercel..."
vercel login

# Deploy to Vercel
echo "Deploying to Vercel..."
vercel --prod

echo "✅ Deployment complete!"
echo "Your site is now live at: https://your-project.vercel.app"
echo "API is available at: https://your-project.vercel.app/api"
