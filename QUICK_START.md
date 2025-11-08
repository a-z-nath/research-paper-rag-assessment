# 🚀 Quick Start Without Docker (Faster Development)

If Docker build is too slow, run services locally for faster development.

## Prerequisites

- Python 3.11+ installed
- Node.js 18+ installed
- Docker Desktop (only for Qdrant)

## Setup Steps

### 1. Start Qdrant Only (Docker)

```powershell
# Pull and run Qdrant (lightweight, fast to start)
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant:latest
```

**Verify:**
```powershell
curl http://localhost:6333/health
```

### 2. Start Backend (Local Python)

```powershell
# Navigate to backend
cd src

# Install dependencies (one-time)
pip install -r requirements.txt

# Set environment variables
# Create .env file with:
# GEMINI_API_KEY=your-key
# QDRANT_HOST=localhost
# QDRANT_PORT=6333

# Run backend
python main.py
```

**Expected output:**
```
🚀 Starting Research Paper RAG System
📡 API: http://0.0.0.0:8000
🤖 LLM: Google Gemini (model: gemini-2.5-flash)
```

### 3. Start Frontend (Local npm)

Open a **new terminal**:

```powershell
# Navigate to frontend
cd frontend

# Install dependencies (one-time, takes 1-2 minutes)
npm install

# Run frontend
npm run dev
```

**Expected output:**
```
ready - started server on 0.0.0.0:3000
```

## 🎯 Access Your Application

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000/docs
- **Qdrant:** http://localhost:6333/dashboard

## 🔧 Development Workflow

**Backend changes:**
- Edit files in `src/`
- Press `Ctrl+C` to stop
- Run `python main.py` again

**Frontend changes:**
- Edit files in `frontend/`
- Changes hot-reload automatically
- No restart needed

## 🛑 Stop Services

```powershell
# Stop backend (Ctrl+C in its terminal)
# Stop frontend (Ctrl+C in its terminal)

# Stop Qdrant
docker stop qdrant

# Remove Qdrant (if needed)
docker rm qdrant
```

## 📦 Persistence

Qdrant data is stored in the Docker container. To persist across restarts:

```powershell
# Run with volume
docker run -d -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  --name qdrant \
  qdrant/qdrant:latest
```

## ⚡ Why This is Faster

- **No build time:** Uses installed Python/Node directly
- **Hot reload:** Frontend updates instantly
- **Quick restart:** Backend restarts in seconds
- **Easy debugging:** Direct access to logs and errors
- **Lighter:** Only Qdrant in Docker (lightweight)

## 🐛 Troubleshooting

### Backend won't start
```powershell
# Check Python version
python --version  # Should be 3.11+

# Check if packages installed
pip list | Select-String "fastapi"

# Reinstall if needed
pip install -r requirements.txt --force-reinstall
```

### Frontend won't start
```powershell
# Check Node version
node --version  # Should be 18+

# Clear cache and reinstall
Remove-Item -Recurse -Force node_modules, .next
npm install
npm run dev
```

### Port conflicts
```powershell
# Check what's using ports
netstat -ano | findstr :8000
netstat -ano | findstr :3000
netstat -ano | findstr :6333

# Kill the process
taskkill /PID <PID> /F
```

## 🔄 Switch Back to Docker Later

When you're ready for full Docker:

```powershell
# Stop local services (Ctrl+C)
# Stop local Qdrant
docker stop qdrant
docker rm qdrant

# Use docker-compose
docker-compose up -d
```

---

**This approach is 10x faster for development!** Use Docker Compose only for production or full system testing.
