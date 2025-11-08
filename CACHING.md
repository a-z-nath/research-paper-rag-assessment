# Query Caching System

## Overview

The RAG system includes an intelligent caching mechanism to speed up responses for repeated queries. When the same or similar questions are asked again, the system can return cached results instantly (< 0.01s) instead of reprocessing the entire RAG pipeline (typically 5-10s).

## Features

### 1. **Smart Query Normalization**
- Questions are normalized (lowercase, whitespace trimmed) before caching
- Case-insensitive matching: "What is AI?" matches "what is ai?"
- Whitespace handling: Extra spaces are removed for consistency
- Parameter-aware: Different `top_k` values or `paper_ids` filters create separate cache entries

### 2. **Time-to-Live (TTL)**
- Cached entries expire after a configurable time (default: 1 hour)
- Prevents stale data from being served indefinitely
- Automatic cleanup of expired entries

### 3. **Automatic Cache Invalidation**
- Cache is cleared when new papers are uploaded
- Specific paper queries are invalidated when papers are deleted
- Ensures fresh results when the knowledge base changes

### 4. **Performance Tracking**
- Hit/miss rate statistics
- Most frequently accessed queries
- Cache size and eviction metrics

## Configuration

Edit `src/.env` to customize cache behavior:

```env
# Enable/disable caching
CACHE_ENABLED=true

# Time-to-live for cached entries (in seconds)
CACHE_TTL_SECONDS=3600  # 1 hour

# Maximum number of cached queries
CACHE_MAX_SIZE=1000
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_ENABLED` | `true` | Enable or disable the caching system |
| `CACHE_TTL_SECONDS` | `3600` | How long cached responses remain valid (in seconds) |
| `CACHE_MAX_SIZE` | `1000` | Maximum number of queries to cache |

## API Endpoints

### Query with Cache
```bash
POST /api/query
```

**Response includes cache indicator:**
```json
{
  "answer": "...",
  "citations": [...],
  "confidence": 0.85,
  "response_time": 0.001,
  "cached": true  // ⚡ Indicates cache hit
}
```

### Get Cache Statistics
```bash
GET /api/cache/stats
```

**Response:**
```json
{
  "enabled": true,
  "cache_size": 45,
  "max_size": 1000,
  "total_hits": 123,
  "total_misses": 78,
  "total_requests": 201,
  "hit_rate_percent": 61.19,
  "evictions": 5,
  "ttl_seconds": 3600,
  "top_cached_queries": [
    {
      "question": "What is machine learning?",
      "hit_count": 15,
      "created_at": "2025-10-31T10:30:00",
      "ttl_seconds": 2400
    }
  ]
}
```

### Clear Cache
```bash
POST /api/cache/clear
```

Clears all cached entries. Useful when:
- Testing new prompts or LLM changes
- Debugging incorrect cached responses
- Forcing fresh answers for all queries

### Cleanup Expired Entries
```bash
POST /api/cache/cleanup
```

Removes only expired entries. Automatically called periodically, but can be triggered manually.

## Performance Benefits

### Before Caching
```
Query 1: "What is transformer architecture?" → 7.2s
Query 2: "What is transformer architecture?" → 7.1s
Query 3: "What is transformer architecture?" → 6.9s
```

### After Caching
```
Query 1: "What is transformer architecture?" → 7.2s (cache miss)
Query 2: "What is transformer architecture?" → 0.001s (cache hit) ⚡
Query 3: "What is transformer architecture?" → 0.001s (cache hit) ⚡
```

**Speed Improvement: ~7000x faster for cached queries!**

## Cache Behavior

### What Gets Cached?
- ✅ Query question
- ✅ Full answer text
- ✅ Citations with page numbers
- ✅ Confidence scores
- ✅ Source papers used
- ✅ Query parameters (top_k, paper_ids)

### When Cache is Invalidated?
- 🔄 New paper uploaded → **All cache cleared**
- 🗑️ Paper deleted → **Queries for that paper invalidated**
- ⏰ TTL expired → **Individual entry removed**
- 📊 Cache full → **Least recently used entry evicted**

### Cache Key Generation
```python
# These queries generate the SAME cache key:
"What is AI?"
"what is ai?"
"  What   is   AI?  "

# These queries generate DIFFERENT cache keys:
"What is AI?" (top_k=5)
"What is AI?" (top_k=10)
```

## Frontend Integration

The frontend displays a "⚡ Cached" badge for instant responses:

```tsx
{result.cached && (
  <span className="bg-green-100 text-green-800">
    ⚡ Cached
  </span>
)}
```

Response time for cached queries shows `< 0.01s` instead of actual time.

## Monitoring Cache Performance

### Check Health Endpoint
```bash
curl http://localhost:8000/health
```

Includes cache status:
```json
{
  "status": "healthy",
  "services": {
    "pdf_processor": true,
    "embedding_service": true,
    "qdrant": true,
    "rag_pipeline": true,
    "query_cache": true  // Cache is enabled
  }
}
```

### View Statistics
```bash
curl http://localhost:8000/api/cache/stats
```

Key metrics:
- **Hit Rate %**: Higher is better (60%+ is excellent)
- **Cache Size**: Current number of cached queries
- **Evictions**: How many entries were removed due to size limits
- **Top Cached Queries**: Most frequently accessed questions

## Best Practices

### 1. **Optimize TTL for Your Use Case**
```env
# Research papers change rarely → Long TTL
CACHE_TTL_SECONDS=86400  # 24 hours

# Frequently updated content → Short TTL
CACHE_TTL_SECONDS=300    # 5 minutes
```

### 2. **Monitor Hit Rate**
- Aim for 40-60% hit rate in typical usage
- Lower hit rate → Consider increasing cache size or TTL
- Higher hit rate → Cache is working well!

### 3. **Clear Cache After Major Changes**
```bash
# After updating LLM prompts
curl -X POST http://localhost:8000/api/cache/clear

# After changing retrieval parameters
curl -X POST http://localhost:8000/api/cache/clear
```

### 4. **Disable During Development**
```env
# In .env
CACHE_ENABLED=false
```

This ensures you always see fresh results when testing changes.

## Troubleshooting

### Cache Not Working?

1. **Check if enabled:**
   ```bash
   curl http://localhost:8000/api/cache/stats
   ```

2. **Verify environment variable:**
   ```bash
   # Should be "true"
   echo $CACHE_ENABLED
   ```

3. **Check startup logs:**
   ```
   ⚡ Cache: ENABLED (TTL: 3600s, Max: 1000 queries)
   ```

### Getting Stale Results?

1. **Clear the cache:**
   ```bash
   curl -X POST http://localhost:8000/api/cache/clear
   ```

2. **Reduce TTL:**
   ```env
   CACHE_TTL_SECONDS=600  # 10 minutes
   ```

### Cache Too Large?

1. **Reduce max size:**
   ```env
   CACHE_MAX_SIZE=500
   ```

2. **Cleanup expired entries:**
   ```bash
   curl -X POST http://localhost:8000/api/cache/cleanup
   ```

## Architecture

```
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Check Cache    │◄──── Query normalization
└────────┬────────┘      (lowercase, trim, hash)
         │
    ┌────┴────┐
    │  Hit?   │
    └─┬────┬──┘
      │    │
   Yes│    │No
      │    │
      ▼    ▼
   ┌────┐ ┌─────────────┐
   │Cache│ │ RAG Pipeline│
   │Hit │ │  (Embed +   │
   └─┬──┘ │   Search +  │
     │    │   Generate) │
     │    └──────┬──────┘
     │           │
     │           ▼
     │    ┌─────────────┐
     │    │ Store in    │
     │    │   Cache     │
     │    └──────┬──────┘
     │           │
     └───────┬───┘
             │
             ▼
      ┌─────────────┐
      │   Return    │
      │  Response   │
      └─────────────┘
```

## Example Usage

### Python
```python
import requests

# First query (cache miss)
response = requests.post("http://localhost:8000/api/query", json={
    "question": "What is attention mechanism?",
    "top_k": 5
})
print(f"Response time: {response.json()['response_time']}s")
# Output: Response time: 7.2s

# Second query (cache hit)
response = requests.post("http://localhost:8000/api/query", json={
    "question": "What is attention mechanism?",
    "top_k": 5
})
print(f"Response time: {response.json()['response_time']}s")
print(f"Cached: {response.json()['cached']}")
# Output: Response time: 0.001s
# Output: Cached: True ⚡
```

### JavaScript (Frontend)
```javascript
const response = await fetch("http://localhost:8000/api/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    question: "What is attention mechanism?",
    top_k: 5
  })
});

const data = await response.json();
if (data.cached) {
  console.log("⚡ Lightning fast response from cache!");
}
```

## Summary

✅ **Automatic**: No code changes needed to benefit from caching  
✅ **Transparent**: Original query results are preserved exactly  
✅ **Smart**: Normalized queries match case-insensitively  
✅ **Safe**: Auto-invalidation prevents stale data  
✅ **Configurable**: Tune TTL and size limits for your needs  
✅ **Observable**: Rich statistics and monitoring endpoints  

The caching system can reduce response times from **5-10 seconds to < 0.01 seconds** for repeated queries, dramatically improving user experience!
