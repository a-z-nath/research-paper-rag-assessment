# 🚀 Quick Start Guide

Get the Research Paper RAG Assistant up and running in minutes.

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Cloud Ollama API key
- Git

## 1. Clone Repository

```bash
git clone https://github.com/a-z-nath/research-paper-rag-assessment.git
cd research-paper-rag-assessment
```

## 2. Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env
cp .env.example docker.env

# Edit .env with your settings (especially Ollama Cloud API key)
nano .env
```

**Important**: Add your Ollama Cloud API key to `.env`:

```bash
OLLAMA_API_KEY=your_ollama_cloud_api_key_here
```

**Important**: Update `docker.env` with Qdrant host and port:

```bash
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

## 4. Start Services with Docker

```bash
# Start all services (Qdrant + PostgreSQL + API)
docker-compose up -d

# Check if services are running
docker-compose ps
```

```bash
# For development with live reload
docker-compose -f docker-compose.dev.yml up -d
```

## 5. Initialize Database

```bash
# Run database migrations
docker-compose exec api python -c "
from src.database import create_tables
create_tables()
print('✅ Database initialized')
"
```

## 6. Test the Application

```bash
# Check health
curl http://localhost:8000/health

# Upload sample papers
curl -X POST "http://localhost:8000/api/papers/upload" \
  -F "files=@sample_papers/paper1_machine_learning.pdf"

# Test query
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the main contribution of this paper?",
    "top_k": 5
  }'
```

## 🎉 You're Ready

Your Research Paper RAG Assistant is now running at `http://localhost:8000`.

- View API documentation: `http://localhost:8000/docs`
- Check system health: `http://localhost:8000/health`

For detailed API usage and advanced configuration, see the main [README.md](README.md).
