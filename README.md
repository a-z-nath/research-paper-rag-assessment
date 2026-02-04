# 🎓 Research Paper RAG Assistant

A production-ready Retrieval-Augmented Generation (RAG) system that helps researchers efficiently query and understand academic papers using vector search and cloud-based LLM integration.

## 🚀 Getting Started

**New to the project?** Check out our [Quick Start Guide](QUICK-START.md) for step-by-step setup instructions.

## 📋 API Documentation

### 🔄 Health Check

```bash
curl http://localhost:8000/health
```

### 📄 Paper Management

#### Upload Papers

```bash
# Single file
curl -X POST "http://localhost:8000/api/papers/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@paper1.pdf"

# Multiple files
curl -X POST "http://localhost:8000/api/papers/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@paper1.pdf" \
  -F "files=@paper2.pdf"
```

#### List Papers

```bash
curl http://localhost:8000/api/papers
```

#### Get Paper Details

```bash
# Without full text
curl http://localhost:8000/api/papers/{paper_id}

# With full text
curl "http://localhost:8000/api/papers/{paper_id}?include_full_text=true"
```

#### Delete Paper

```bash
curl -X DELETE http://localhost:8000/api/papers/{paper_id}
```

### 🔍 Query System

#### Query Papers

```bash
# Basic query
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main contributions of transformer architecture?",
    "top_k": 5
  }'

# Query specific papers
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Compare CNN and transformer approaches",
    "top_k": 10,
    "paper_ids": ["paper-uuid-1", "paper-uuid-2"]
  }'
```

#### Query History

```bash
curl "http://localhost:8000/api/queries/history?limit=10&offset=0"
```

### 📊 Analytics

#### Popular Topics

```bash
# Last 30 days
curl "http://localhost:8000/api/analytics/popular?days=30&limit=10"

# All time with minimum count
curl "http://localhost:8000/api/analytics/popular?days=0&limit=15&min_count=3"

# Force rebuild topics
curl "http://localhost:8000/api/analytics/popular?force_rebuild=true"
```

#### RAG Pipeline Health

```bash
curl http://localhost:8000/api/rag/health
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Layer                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │   Paper APIs    │ │   Query APIs    │ │ Analytics APIs  │    │
│  │  - Upload       │ │  - RAG Pipeline │ │  - TF-IDF       │    │
│  │  - Management   │ │  - Query Hist   │ │  - Topics       │    │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
│                               │                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                Service Layer                            │    │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │    │
│  │ │PDF Processor│ │Text Chunker │ │  Embedding Service  │ │    │
│  │ │- Extract    │ │- Section    │ │  - SentenceTransf   │ │    │
│  │ │- Metadata   │ │- Semantic   │ │  - Batch Process    │ │    │
│  │ └─────────────┘ └─────────────┘ └─────────────────────┘ │    │
│  │                                                         │    │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │    │
│  │ │RAG Pipeline │ │Batch Process│ │  TF-IDF Service     │ │    │
│  │ │- Retrieval  │ │- Multi-file │ │  - Topic Extract    │ │    │
│  │ │- Generation │ │- Error Hand │ │  - Timeline Cache   │ │    │
│  │ └─────────────┘ └─────────────┘ └─────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────┬─────────────────┬─────────────────┬──────────────┘
               │                 │                 │
┌──────────────▼──────────────┐ ┌▼────────────────┐ ┌▼──────────────┐
│        Qdrant Vector DB     │ │   PostgreSQL    │ │ Ollama Cloud  │
│  - Embeddings Storage       │ │  - Papers       │ │  - LLM Gen    │
│  - Similarity Search        │ │  - Chunks       │ │  - llama3     │
│  - Metadata Filtering       │ │  - Queries      │ │  - Cloud API  │
│  - Collection Management    │ │  - Analytics    │ │  - Scalable   │
└─────────────────────────────┘ └─────────────────┘ └───────────────┘
```

## 💾 Database Schema

### Core Tables

- **papers**: Metadata, full text, upload info
- **chunks**: Text segments with embeddings refs
- **queries**: User questions and responses
- **paper_stats**: Usage analytics per paper
- **topic_analytics**: TF-IDF topic cache
- **topic_generation_log**: Processing timeline

## � Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/research_rag_db

# Qdrant Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Cloud Ollama Configuration
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_API_KEY=your_ollama_cloud_api_key_here
OLLAMA_MODEL=deepseek-v3.1:671b-cloud

# Application
DEBUG=true
APP_NAME=Research Paper RAG System
APP_VERSION=1.0.0
```

## 🧪 Testing

### Test with Sample Data

```bash
# Upload all test papers
curl -X POST "http://localhost:8000/api/papers/upload" \
  -F "files=@sample_papers/paper1_machine_learning.pdf" \
  -F "files=@sample_papers/paper2_neural_networks.pdf" \
  -F "files=@sample_papers/paper3_nlp_transformers.pdf" \
  -F "files=@sample_papers/paper4_computer_vision.pdf" \
  -F "files=@sample_papers/paper5_reinforcement_learning.pdf"

# Test query from test_queries.json
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the main contribution of the paper?",
    "top_k": 5
  }'
```

### Run Health Checks

```bash
# Check all services
curl http://localhost:8000/health

# Check RAG pipeline specifically
curl http://localhost:8000/api/rag/health
```

## 📦 Project Structure

```
src/
├── main.py                 # FastAPI application entry
├── config.py              # Configuration management
├── database.py            # Database connection & models
├── api/
│   ├── routes.py          # Paper management endpoints
│   └── query.py           # Query & analytics endpoints
├── models/
│   ├── paper.py           # Paper data model
│   ├── chunk.py           # Text chunk model
│   ├── query.py           # Query history model
│   ├── paper_stats.py     # Analytics model
│   └── topic_analytics.py # Topic cache model
├── schemas/
│   ├── paper.py           # API request/response schemas
│   ├── query.py           # Query schemas
│   └── upload.py          # Upload schemas
└── services/
    ├── pdf_processor.py    # PDF text extraction
    ├── text_chunker.py     # Semantic chunking
    ├── embedding_service.py # Vector embeddings
    ├── qdrant_client.py    # Vector database client
    ├── rag_pipeline.py     # RAG query processing
    ├── batch_processor.py  # Multi-file processing
    └── tfidf_topic_service.py # Topic analytics
```

## 🚨 Troubleshooting

### Common Issues

#### "Cannot connect to Qdrant"

```bash
# Check if Qdrant is running
docker-compose ps

# Restart services
docker-compose restart qdrant
```

#### "Database connection failed"

```bash
# Check PostgreSQL connection
docker-compose exec postgres psql -U user -d research_papers

# Recreate database
docker-compose exec api python -c "from src.database import create_tables; create_tables()"
```

#### "Ollama Cloud API not responding"

```bash
# Check your API key in .env file
grep OLLAMA_API_KEY .env

# Test API connection
curl -H "Authorization: Bearer YOUR_API_KEY" https://ollama.com/api/v1/models
```

#### "Embedding model download slow"

- First run downloads ~90MB model
- Check internet connection
- Model cached in `~/.cache/torch/sentence_transformers/`

### Performance Issues

#### Slow uploads

- Check chunk size configuration in `text_chunker.py`
- Monitor Qdrant storage space
- Verify embedding batch size

#### Query timeouts

- Check Ollama Cloud response time
- Verify Qdrant index status
- Monitor database query performance

## � Performance Metrics

### Expected Performance

- **PDF Processing**: ~2-5 seconds per paper
- **Query Response**: ~1-3 seconds (cached topics)
- **Cold Query**: ~3-8 seconds (includes Cloud LLM)
- **Upload Batch**: ~30-60 seconds for 5 papers

### Optimization Tips

- Use TF-IDF topic caching for analytics
- Batch upload multiple papers
- Monitor embedding cache hits
- Keep Qdrant collection optimized

## 🔒 Security Notes

- Cloud API keys stored in environment variables
- File uploads limited to PDF only
- SQL injection protected via SQLAlchemy ORM
- Input validation on all endpoints
- No authentication implemented (development only)

## 🐳 Docker Deployment

### Development

```bash
docker compose up -d
```

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Need Help?** Open an issue or check the troubleshooting section above.

**API Documentation**: Visit http://localhost:8000/docs when running locally.
