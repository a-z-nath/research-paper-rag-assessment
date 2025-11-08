# Research Paper RAG System - Setup and Installation Guide

## 🎯 What We Built

A production-ready RAG (Retrieval-Augmented Generation) system that helps researchers query academic papers using:
- **Qdrant** for vector storage
- **Google Gemini** for answer generation
- **sentence-transformers** for embeddings
- **FastAPI** for REST API
- **SQLite** for metadata storage

---

## 📦 Prerequisites

✅ You have already set up:
- Docker with Qdrant running on port 6333
- Google Gemini API key
- Python 3.10+

---

## 🚀 Quick Start

### Step 1: Install Python Dependencies

```powershell
# Navigate to Rag directory
cd "c:\Users\Nobel\Desktop\Projects\Intern Project\research-paper-rag-assessment\Rag"

# Install dependencies (this will take a few minutes)
pip install -r requirements.txt
```

### Step 2: Verify Services

```powershell
# Check Qdrant is running
curl http://localhost:6333

# Verify Gemini API key is set in .env
# GEMINI_API_KEY=your-key-here
```

### Step 3: Start the RAG System

```powershell
# Run the application
python main.py
```

You should see:
```
============================================================
🚀 Starting Research Paper RAG System
============================================================
📡 API: http://0.0.0.0:8000
📚 Docs: http://0.0.0.0:8000/docs
🔍 Qdrant: localhost:6333
🤖 LLM: Google Gemini (model: gemini-2.5-flash)
============================================================
```

### Step 4: Test the API

Open a new PowerShell window and test:

```powershell
# Test health endpoint
curl http://localhost:8000/health

# View API documentation
# Open browser: http://localhost:8000/docs
```

---

## 📚 Upload Sample Papers

### Using PowerShell:

```powershell
# Navigate to project root
cd "c:\Users\Nobel\Desktop\Projects\Intern Project\research-paper-rag-assessment"

# Upload paper 1
curl -X POST "http://localhost:8000/api/papers/upload" `
  -F "file=@sample_papers/paper_1.pdf"

# Upload paper 2
curl -X POST "http://localhost:8000/api/papers/upload" `
  -F "file=@sample_papers/paper_2.pdf"

# Upload paper 3
curl -X POST "http://localhost:8000/api/papers/upload" `
  -F "file=@sample_papers/paper_3.pdf"

# Upload paper 4
curl -X POST "http://localhost:8000/api/papers/upload" `
  -F "file=@sample_papers/paper_4.pdf"

# Upload paper 5
curl -X POST "http://localhost:8000/api/papers/upload" `
  -F "file=@sample_papers/paper_5.pdf"
```

### Using Browser (Easier):
1. Go to http://localhost:8000/docs
2. Click on `POST /api/papers/upload`
3. Click "Try it out"
4. Choose file and click "Execute"
5. Repeat for all 5 papers

---

## 🔍 Query the Papers

### Using PowerShell:

```powershell
# Query all papers
$body = @{
    question = "What methodology was used in the transformer paper?"
    top_k = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

### Using Browser:
1. Go to http://localhost:8000/docs
2. Click on `POST /api/query`
3. Click "Try it out"
4. Enter your question
5. Click "Execute"

---

## 📋 Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/papers/upload` | POST | Upload a research paper |
| `/api/query` | POST | Query papers with RAG |
| `/api/papers` | GET | List all papers |
| `/api/papers/{id}` | GET | Get paper details |
| `/api/papers/{id}` | DELETE | Delete a paper |
| `/api/papers/{id}/stats` | GET | Get paper statistics |
| `/api/queries/history` | GET | View query history |
| `/api/analytics/popular` | GET | Popular topics |
| `/health` | GET | Health check |

---

## 🧪 Test Queries

Try these questions:

1. "What is the main goal of the paper 'Attention is All You Need'?"
2. "Which activation functions are commonly used in neural networks?"
3. "Compare the performance of CNNs and Transformers for image recognition."
4. "What datasets are used to evaluate computer vision models?"
5. "How is reinforcement learning applied to decision-making?"

---

## 🐛 Troubleshooting

### Error: "Import sentence_transformers could not be resolved"
- This is just a linter warning, the code will run fine after installing requirements.txt

### Error: "Connection refused to Qdrant"
```powershell
# Start Qdrant
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

### Error: "Gemini API error" or "Invalid API key"
```powershell
# Verify your Gemini API key is correct in src/.env
# GEMINI_API_KEY=your-valid-key-here

# Get a new key at: https://aistudio.google.com/app/apikey

# Restart backend after updating .env
cd src
python main.py
```

### Error: "Rate limit exceeded"
Gemini free tier has rate limits (60 requests/min). Wait a minute and try again.

### Error: "Module not found"
```powershell
# Make sure you're in the Rag directory
cd Rag
pip install -r requirements.txt
```

---

## 📊 Project Structure

```
Rag/
├── main.py                  # Main application entry point
├── config.py                # Configuration settings
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
├── models/
│   ├── __init__.py         # Database initialization
│   ├── database.py         # SQLAlchemy models
│   └── schemas.py          # Pydantic schemas
├── services/
│   ├── __init__.py
│   ├── pdf_processor.py    # PDF extraction & chunking
│   ├── embedding_service.py # Embedding generation
│   ├── qdrant_client.py    # Vector database client
│   └── rag_pipeline.py     # RAG orchestration
└── api/
    ├── __init__.py
    └── routes.py            # API endpoints
```

---

## 🎉 Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Start the server: `python main.py`
3. ✅ Upload papers via http://localhost:8000/docs
4. ✅ Query papers and test the RAG system
5. 📝 Document your approach in APPROACH.md
6. 📝 Update README.md with your findings

---

## 💡 Tips

- Use the interactive docs at `/docs` - it's much easier than curl
- Upload papers one at a time and wait for processing to complete
- Start with simple queries before trying complex ones
- Check `/api/queries/history` to see your query history
- Monitor the console logs for debugging

---

**Ready to start? Run `pip install -r requirements.txt` first!**
