@echo off
REM ReefVoice Quick Deploy Script for Windows

echo 🌊 ReefVoice Deployment Script
echo ================================

REM Check if git is initialized
if not exist ".git" (
    echo Initializing git repository...
    git init
    git add .
    git commit -m "Initial commit"
    git branch -M main
)

REM Check if vercel CLI is installed
where vercel >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing Vercel CLI...
    npm install -g vercel
)

REM Authenticate with Vercel
echo Authenticating with Vercel...
call vercel login

REM Deploy to Vercel
echo Deploying to Vercel...
call vercel --prod

echo.
echo ✅ Deployment complete!
echo Your site is now live at: https://your-project.vercel.app
echo API is available at: https://your-project.vercel.app/api
