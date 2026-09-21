@echo off
echo Cleaning up any old processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do taskkill /F /PID %%a 2>NUL
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>NUL

echo Starting the Backend API (Port 8000)...
cd server
set DATA_DIR=..\data_v2
set GROUND_TRUTH=..\data_v2\ground_truth.json
start "Backend" cmd /k "python -m uvicorn app:app --env-file .env --port 8000"
cd ..

echo Starting the Frontend Vite Server (Port 5173)...
cd client
start "Frontend" cmd /k "npm run dev"
cd ..

echo Servers are starting! Please wait a few seconds and then open:
echo http://localhost:5173/
