# 🎓 Research Paper RAG System

> **An intelligent assistant for querying and understanding academic research papers using Retrieval-Augmented Generation (RAG)**

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red.svg)](https://qdrant.tech/)
[![Gemini](https://img.shields.io/badge/Google-Gemini-blue.svg)](https://ai.google.dev/)

## 📖 Overview

This is a production-ready RAG (Retrieval-Augmented Generation) system that enables researchers to efficiently query academic papers and get AI-powered answers with accurate citations. Instead of manually reading through multiple papers for hours, researchers can now get instant, contextual answers with page-specific citations.

### ✨ Key Features

- 📄 **PDF Document Ingestion** - Upload research papers with automatic text extraction and intelligent chunking
- 🔍 **Semantic Search** - Vector-based similarity search using Qdrant for highly relevant content retrieval
- 🤖 **AI-Powered Q&A** - Generate accurate answers using Google Gemini with proper citations
- 📊 **Query Analytics** - Track query history, confidence scores, and response times
- ⚡ **Smart Caching** - 700-1000x faster responses for repeated queries
- 🎨 **Modern Web UI** - Clean, responsive interface built with Next.js and Tailwind CSS

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **LLM**: Google Gemini API (gemini-2.5-flash)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (384-dimensional)
- **Vector Database**: Qdrant (1.7+)
- **Metadata Storage**: SQLite
- **PDF Processing**: PyPDF2 + LangChain

### Frontend
- **Framework**: Next.js 14 (React 18)
- **Styling**: Tailwind CSS
- **Markdown Rendering**: react-markdown

### Infrastructure
- **Containerization**: Docker (for Qdrant)
- **API Documentation**: Swagger/OpenAPI (FastAPI auto-generated)

---

## 📋 Implemented Features

### ✅ Core Functionality

#### 1. 📄 Document Ingestion System
- Upload PDF research papers via REST API or Web UI
- Automatic metadata extraction (title, authors, year, page count)
- Section-aware chunking (Abstract, Introduction, Methods, Results, Discussion, Conclusion)
- Intelligent text splitting (500 chars with 50 char overlap)
- Vector embedding generation (384-dimensional)
- Batch storage in Qdrant with metadata payloads

**Performance**: Process 10-page papers in ~4 seconds

#### 2. 🔍 Intelligent Query System
- Natural language question answering
- Semantic search with configurable top-k results (1-20)
- Optional paper filtering (query specific papers only)
- Confidence scoring (0.0-1.0)
- Page-specific citations with relevance scores
- Response time tracking
- Query history persistence

**Response Format**:
```json
{
  "answer": "Detailed answer with markdown formatting...",
  "citations": [
    {
      "paper_title": "Attention is All You Need",
      "section": "Methods",
      "page": 3,
      "relevance_score": 0.89,
      "chunk_text": "Relevant excerpt..."
    }
  ],
  "sources_used": ["paper1.pdf", "paper2.pdf"],
  "confidence": 0.85,
  "response_time": 7.2,
  "cached": false
}
```

#### 3. 📚 Paper Management
- `GET /api/papers` - List all uploaded papers
- `GET /api/papers/{id}` - Get paper details
- `DELETE /api/papers/{id}` - Remove paper and its vectors
- `GET /api/papers/{id}/stats` - View paper statistics
- Upload date tracking
- Processing status monitoring

#### 4. 📊 Query History & Analytics
- `GET /api/queries/history` - Recent query history (paginated)
- `GET /api/analytics/popular` - Most queried topics
- Full query log with timestamps
- Confidence and response time metrics
- Source paper tracking

#### 5. ⚡ Smart Caching System
- In-memory LRU cache with TTL (default: 1 hour)
- Query normalization (case-insensitive, whitespace-agnostic)
- 700-1000x speedup for repeated queries (< 0.01s vs 7-10s)
- Automatic cache invalidation on data changes
- `GET /api/cache/stats` - Cache performance metrics
- `POST /api/cache/clear` - Manual cache clearing

**Cache Hit Example**: Same query goes from 7.2s → 0.001s ⚡

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│                  (Next.js + React + Tailwind)                   │
│          Upload UI │ Query Interface │ History Dashboard         │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Port 8000)                    │
│                                                                  │
│  ┌────────────────────┐           ┌──────────────────────────┐   │
│  │  PDF Processor     │           │    RAG Pipeline          │   │
│  │  - Extract text    │           │  - Query embedding       │   │
│  │  - Section detect  │           │  - Vector search         │   │
│  │  - Chunk (500ch)   │           │  - Context assembly      │   │
│  │  - Generate embed  │           │  - LLM generation        │   │
│  └────────────────────┘           │  - Citation extraction   │   │
│                                   └──────────────────────────┘   │
│                                                                  │
│  ┌────────────────────┐           ┌──────────────────────────┐   │
│  │  Cache Service     │           │    LLM Service           │   │
│  │  - Query normalize │           │  - Google Gemini API     │   │
│  │  - LRU eviction    │           │  - Prompt engineering    │   │
│  │  - TTL: 1 hour     │           │  - Response parsing      │   │
│  └────────────────────┘           └──────────────────────────┘   │
└───────┬──────────────────┬──────────────────┬───────────────────-┘
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌──────────────────┐
│   Qdrant      │  │   SQLite      │  │  Google Gemini   │
│   (Vector DB) │  │   (Metadata)  │  │  API (LLM)       │
│               │  │               │  │                  │
│ - 384D vectors│  │ - Papers      │  │ - gemini-2.5-    │
│ - Cosine sim  │  │ - Queries     │  │   flash model    │
│ - Port 6333   │  │ - Analytics   │  │ - Rate: 15 RPM   │
└───────────────┘  └───────────────┘  └──────────────────┘
```

### Data Flow

**Upload Flow**:
```
PDF → Extract Text → Chunk → Embed → Store (Qdrant + SQLite)
```

**Query Flow**:
```
Question → Check Cache → [Miss] → Embed → Search Qdrant → 
Generate Answer (Gemini) → Extract Citations → Cache → Return
```

---

## 📊 Project Structure

```
research-paper-rag-assessment/
├── src/                           # Backend (Python/FastAPI)
│   ├── main.py                    # Application entry point
│   ├── config.py                  # Configuration management
│   ├── requirements.txt           # Python dependencies
│   ├── .env                       # Environment variables (API keys)
│   │
│   ├── api/
│   │   └── routes.py              # REST API endpoints
│   │
│   ├── models/
│   │   ├── database.py            # SQLAlchemy ORM models
│   │   └── schemas.py             # Pydantic request/response schemas
│   │
│   └── services/
│       ├── pdf_processor.py       # PDF extraction & chunking
│       ├── embedding_service.py   # Text → Vector embeddings
│       ├── qdrant_client.py       # Vector database operations
│       ├── llm_service.py         # Google Gemini integration
│       ├── rag_pipeline.py        # RAG orchestration
│       └── cache_service.py       # Query caching logic
│
├── frontend/                      # Frontend (Next.js)
│   ├── app/
│   │   ├── page.tsx               # Home page
│   │   ├── upload/page.tsx        # Upload interface
│   │   ├── query/page.tsx         # Query interface
│   │   ├── papers/page.tsx        # Paper management
│   │   └── history/page.tsx       # Query history
│   ├── package.json               # Node dependencies
│   └── tailwind.config.ts         # Tailwind configuration
│
├── sample_papers/                 # Test dataset (5 PDFs)

├── .gitignore                     # Git ignore rules (protects API keys)
│
├── README.md                      # This file (main documentation)
├── APPROACH.md                    # Technical design decisions
├── CACHING.md                     # Caching system documentation
└── test_queries.json              # Sample test queries
```

---

## 🚀 Getting Started

### Prerequisites

Before running the application, ensure you have the following installed:

| Software | Version | Purpose | Download Link |
|----------|---------|---------|---------------|
| **Python** | 3.11+ | Backend runtime | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ | Frontend runtime | [nodejs.org](https://nodejs.org/) |
| **Docker Desktop** | Latest | Qdrant vector database | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Git** | Latest | Version control | [git-scm.com](https://git-scm.com/) |

**Required API Key**:
- Google Gemini API Key (Free tier available) - Get it from [Google AI Studio](https://makersuite.google.com/app/apikey)

---

## 📥 Quick Start (10 minutes)

### Step 1: Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/research-paper-rag-assessment.git
cd research-paper-rag-assessment
```

### Step 2: Start Qdrant Vector Database

```bash
# Install Docker Desktop first, then:
docker run -d -p 6333:6333 qdrant/qdrant
# Verify: http://localhost:6333/dashboard
```

### Step 3: Setup Backend

```bash
cd src

# Copy environment template and add your Gemini API key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your-actual-key-here

# Install Python dependencies
pip install -r requirements.txt

# Run backend server
python main.py
# Backend runs on http://localhost:8000
```

**Expected output**:
```
🔧 Initializing database...
✅ Database initialized successfully
🔧 Initializing services...
  Loading PDF processor...
  Loading embedding model...
  Connecting to Qdrant...
✅ Qdrant collection exists: research_papers
  Initializing LLM service (Gemini)...
  Initializing RAG pipeline...
  Initializing query cache...

============================================================
🚀 Starting Research Paper RAG System
============================================================
📡 API: http://0.0.0.0:8000
📚 Docs: http://0.0.0.0:8000/docs
🔍 Qdrant: localhost:6333
🤖 LLM: Google Gemini (model: gemini-2.5-flash)
⚡ Cache: ENABLED (TTL: 3600s, Max: 1000 queries)
============================================================

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Verify backend is running**:
- Open browser: http://localhost:8000
- API docs: http://localhost:8000/docs

### Step 4: Setup Frontend

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
# Frontend runs on http://localhost:3000
```

**Access the application**:
- Open browser: http://localhost:3000

### Step 5: Test the System

```bash
# Method 1: Use the Web UI
# Open http://localhost:3000 in your browser
# Upload a PDF and ask questions

# Method 2: Use API directly
# Upload a paper
curl -X POST "http://localhost:8000/api/papers/upload" \
  -F "file=@path/to/your/paper.pdf"

# Query the paper
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What methodology was used?", "top_k": 5}'
```

### Step 6: View API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🎯 Quick Start Guide

### 1️⃣ Upload Papers

1. Navigate to http://localhost:3000
2. Click **"Upload Papers"**
3. Select a PDF from `sample_papers/` directory
4. Wait for processing (~4 seconds per paper)
5. Repeat for all 5 sample papers

### 2️⃣ Ask Questions

1. Click **"Query Papers"**
2. Enter a question (e.g., "What methodology was used in the transformer paper?")
3. Adjust top-k results slider (default: 5)
4. Click **"Ask Question"**
5. View AI-generated answer with citations

### 3️⃣ View History

1. Click **"Query History"**
2. See all past queries with timestamps
3. Review confidence scores and response times

### 4️⃣ Manage Papers

1. Click **"View Papers"**
2. See all uploaded papers with metadata
3. Delete papers if needed (also removes vectors)

---

## � API Documentation

### Base URL
```
http://localhost:8000
```

### Interactive API Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Core Endpoints

#### 📄 Paper Management

**Upload Paper**
```http
POST /api/papers/upload
Content-Type: multipart/form-data

file: <PDF file>
```

**Response**:
```json
{
  "paper_id": 1,
  "title": "Attention is All You Need",
  "filename": "paper3_nlp_transformers.pdf",
  "total_pages": 15,
  "chunk_count": 42,
  "message": "Paper uploaded and processed successfully"
}
```

**List All Papers**
```http
GET /api/papers?skip=0&limit=100
```

**Get Paper Details**
```http
GET /api/papers/{paper_id}
```

**Delete Paper**
```http
DELETE /api/papers/{paper_id}
```

**Get Paper Statistics**
```http
GET /api/papers/{paper_id}/stats
```

#### 🔍 Query System

**Ask Question**
```http
POST /api/query
Content-Type: application/json

{
  "question": "What methodology was used in the transformer paper?",
  "top_k": 5,
  "paper_ids": null  // Optional: [1, 3] to filter specific papers
}
```

**Response**:
```json
{
  "answer": "The transformer paper introduces a novel architecture...",
  "citations": [
    {
      "paper_title": "Attention is All You Need",
      "section": "Methods",
      "page": 3,
      "relevance_score": 0.89,
      "chunk_text": "We propose a new simple network..."
    }
  ],
  "sources_used": ["paper3_nlp_transformers.pdf"],
  "confidence": 0.85,
  "response_time": 7.2,
  "cached": false
}
```

#### 📊 Analytics

**Query History**
```http
GET /api/queries/history?skip=0&limit=50
```

**Popular Topics**
```http
GET /api/analytics/popular?limit=10
```

**Cache Statistics**
```http
GET /api/cache/stats
```

**Clear Cache**
```http
POST /api/cache/clear
```

#### 🏥 Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "services": {
    "pdf_processor": true,
    "embedding_service": true,
    "qdrant": true,
    "rag_pipeline": true,
    "query_cache": true
  }
}
```

### Example cURL Commands

```bash
# Upload a paper
curl -X POST "http://localhost:8000/api/papers/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_papers/paper1_machine_learning.pdf"

# Ask a question
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?",
    "top_k": 5
  }'

# Get query history
curl -X GET "http://localhost:8000/api/queries/history?limit=10"

# Check cache stats
curl -X GET "http://localhost:8000/api/cache/stats"
```

---

## 🧪 Testing

### Test with Sample Papers

5 sample research papers are provided in `sample_papers/`:

1. `paper1_machine_learning.pdf` - Classic ML algorithms
2. `paper2_neural_networks.pdf` - Deep learning architectures
3. `paper3_nlp_transformers.pdf` - Transformer models
4. `paper4_computer_vision.pdf` - CNN and vision models
5. `paper5_reinforcement_learning.pdf` - RL algorithms

### Test Queries

20 test queries are provided in `test_queries.json`:

```json
[
  {
    "query": "What is machine learning?",
    "difficulty": "easy",
    "expected_papers": ["paper1"]
  },
  {
    "query": "Compare CNNs and Transformers for image classification",
    "difficulty": "hard",
    "expected_papers": ["paper3", "paper4"]
  }
]
```

### Running Tests

```bash
# Upload all sample papers
python scripts/upload_test_papers.py

# Run test queries
python scripts/test_queries.py

# Check results
python scripts/evaluate_results.py
```

---

## 📈 Performance Metrics

### Upload Performance
- **10-page paper**: ~4 seconds
- **PDF extraction**: 1.2s (30%)
- **Embedding**: 2.3s (57%)
- **Vector storage**: 0.5s (13%)

### Query Performance
- **Cold query** (no cache): 7-10 seconds
  - Embedding: 0.2s (2%)
  - Vector search: 0.3s (4%)
  - LLM generation: 7.2s (86%)
  - Database save: 0.1s (1%)
- **Cached query**: < 0.01 seconds ⚡ (700-1000x faster!)

### Cache Statistics
- **Hit rate**: 40-60% (typical usage)
- **TTL**: 1 hour (configurable)
- **Max size**: 1000 queries
- **Memory usage**: ~2 MB

---

## 🛡️ Security

### API Key Protection

**❌ NEVER commit these files:**
- `.env`
- `.env.local`

- `src/.env`

These are already in `.gitignore`.

**✅ Safe to commit:**
- `.env.example` (with placeholder values)

### If You Accidentally Exposed Your API Key

1. **Revoke the key immediately**:
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Delete the exposed key
   - Generate a new one

2. **Update your local `.env`**:
   ```env
   GEMINI_API_KEY=your_new_key_here
   ```

3. **Remove from git history** (if already pushed):
   ```bash
   # Use BFG Repo-Cleaner or git filter-branch
   # Contact repository maintainer if needed
   ```

---

## 🔍 Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Problem**: `ConnectionError: Could not connect to Qdrant`
```bash
# Solution: Ensure Qdrant is running
docker ps
docker run -d -p 6333:6333 qdrant/qdrant
```

**Problem**: `google.api_core.exceptions.InvalidArgument: API key not valid`
```bash
# Solution: Check your .env file
cat src/.env  # Linux/Mac
type src\.env  # Windows

# Verify GEMINI_API_KEY is set correctly
```

### Frontend Issues

**Problem**: `Module not found: Can't resolve 'react-markdown'`
```bash
# Solution: Install dependencies
cd frontend
npm install
```

**Problem**: `Error: listen EADDRINUSE: address already in use :::3000`
```bash
# Solution: Kill process using port 3000
# Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:3000 | xargs kill -9
```

---

## 📚 Additional Documentation

- **[APPROACH.md](APPROACH.md)** - Detailed technical design decisions
  - Chunking strategy (why 500 chars?)
  - Embedding model choice (why all-MiniLM-L6-v2?)
  - Prompt engineering techniques
  - Database schema rationale
  - Trade-offs and limitations

- **[CACHING.md](CACHING.md)** - Query caching system documentation
  - How caching works
  - Performance benefits
  - Configuration options
  - Cache management API

- **[SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md)** - How to submit your work

- **[PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md)** - PR guidelines

---

## 🤝 Contributing

This project was developed as part of a technical assessment. For improvements or bug fixes:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -m 'Add some improvement'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Open a Pull Request

---

## 📄 License

This project is part of a technical assessment. All rights reserved.

---

## 👤 Author

**Nobel Badhon Ahmad**
- GitHub: [@BadhonAhmad](https://github.com/BadhonAhmad)
- Branch: `submission/Nobel-Badhon`

---

## � Acknowledgments

- Google Gemini API for LLM capabilities
- Qdrant for efficient vector search
- LangChain for RAG utilities
- sentence-transformers for embedding models
- FastAPI for the excellent web framework
- Next.js team for the React framework

---

## 📞 Support

For questions or issues:
- 📧 Email: ahmadbadhon28@gmail.com
- 🐛 GitHub Issues: [Create an issue](https://github.com/BadhonAhmad/research-paper-rag-assessment/issues)

---

**Built with ❤️ for AI-powered research assistance**