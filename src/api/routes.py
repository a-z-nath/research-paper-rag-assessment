"""
API routes for RAG system
"""
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session
from typing import List, Optional
import tempfile
import os
import shutil
from datetime import datetime

from models.database import Paper, Query as QueryModel
from models.schemas import (
    PaperUploadResponse, QueryRequest, QueryResponse,
    PaperDetail, QueryHistory, PaperStats
)
from models import get_db
from services.pdf_processor import PDFProcessor
from services.embedding_service import EmbeddingService
from services.qdrant_client import QdrantService
from services.rag_pipeline import RAGPipeline
from services.cache_service import QueryCache
import config

# Initialize services (will be injected in main.py)
pdf_processor = None
embedding_service = None
qdrant_service = None
rag_pipeline = None
query_cache = None

router = APIRouter()


def init_services(
    pdf_proc: PDFProcessor,
    embed_svc: EmbeddingService,
    qdrant_svc: QdrantService,
    rag_pipe: RAGPipeline,
    cache: Optional[QueryCache] = None
):
    """Initialize services for routes"""
    global pdf_processor, embedding_service, qdrant_service, rag_pipeline, query_cache
    pdf_processor = pdf_proc
    embedding_service = embed_svc
    qdrant_service = qdrant_svc
    rag_pipeline = rag_pipe
    query_cache = cache


@router.post("/api/papers/upload", response_model=PaperUploadResponse)
async def upload_paper(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a research paper PDF
    
    - Extracts metadata (title, authors, year)
    - Creates semantic chunks
    - Generates embeddings
    - Stores in Qdrant and database
    """
    print(f"\n📤 [UPLOAD] Starting paper upload: {file.filename}")
    
    # Validate file
    if not file.filename:
        print("❌ [UPLOAD] Error: No filename provided")
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename.endswith('.pdf'):
        print(f"❌ [UPLOAD] Error: Invalid file type - {file.filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only PDF files are supported. Received: {file.filename}"
        )
    
    # Check file size (50 MB limit)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > 50 * 1024 * 1024:  # 50 MB
        print(f"❌ [UPLOAD] Error: File too large - {file_size / (1024*1024):.2f} MB")
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is 50 MB. Your file: {file_size / (1024*1024):.2f} MB"
        )
    
    if file_size == 0:
        print("❌ [UPLOAD] Error: Empty file")
        raise HTTPException(status_code=400, detail="File is empty")
    
    print(f"✅ [UPLOAD] File validation passed - Size: {file_size / (1024*1024):.2f} MB")
    
    # Check if paper already exists
    existing = db.query(Paper).filter(Paper.filename == file.filename).first()
    if existing:
        print(f"❌ [UPLOAD] Error: Duplicate paper - {file.filename} already exists (ID: {existing.id})")
        raise HTTPException(
            status_code=400,
            detail=f"Paper '{file.filename}' already exists with ID {existing.id}. Delete it first or rename the file."
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    try:
        # Process PDF - Extract text and create chunks
        print(f"📄 [UPLOAD] Processing PDF: {file.filename}")
        chunks, metadata = pdf_processor.process_pdf(tmp_path)
        print(f"✅ [UPLOAD] PDF processed - {len(chunks)} chunks created")
        print(f"   Title: {metadata.get('title', 'N/A')}")
        print(f"   Authors: {metadata.get('authors', 'N/A')}")
        print(f"   Year: {metadata.get('year', 'N/A')}")
        print(f"   Pages: {metadata.get('total_pages', 'N/A')}")
        
        if not chunks:
            print("❌ [UPLOAD] Error: No text extracted from PDF")
            raise HTTPException(
                status_code=400,
                detail="Failed to extract text from PDF. The file may be corrupted, password-protected, or contain only images."
            )
        
        # Create paper record in database
        print(f"💾 [UPLOAD] Creating database record for paper")
        paper = Paper(
            title=metadata['title'],
            authors=metadata['authors'],
            year=metadata['year'],
            filename=file.filename,
            file_path=tmp_path,
            total_pages=metadata['total_pages'],
            processed=0,  # Processing status
            chunk_count=len(chunks)
        )
        db.add(paper)
        db.commit()
        db.refresh(paper)
        print(f"✅ [UPLOAD] Paper record created with ID: {paper.id}")
        
        # Generate embeddings for all chunks
        print(f"🔢 [UPLOAD] Generating embeddings for {len(chunks)} chunks...")
        chunk_texts = [chunk.page_content for chunk in chunks]
        embeddings = embedding_service.embed_texts(chunk_texts)
        print(f"✅ [UPLOAD] Embeddings generated successfully")
        
        # Prepare payloads
        payloads = []
        for chunk in chunks:
            payloads.append({
                'text': chunk.page_content,
                'page': chunk.metadata.get('page'),
                'section': chunk.metadata.get('section'),
                'title': metadata['title'],
                'chunk_index': chunk.metadata.get('chunk_index')
            })
        
        # Store in Qdrant vector database
        print(f"🗄️  [UPLOAD] Storing vectors in Qdrant...")
        stored_count = qdrant_service.add_vectors(embeddings, payloads, paper.id)
        print(f"✅ [UPLOAD] {stored_count} vectors stored in Qdrant")
        
        # Update paper status to processed
        paper.processed = 1
        paper.chunk_count = stored_count
        db.commit()
        print(f"✅ [UPLOAD] Paper status updated to processed")
        
        # Clear cache since new content is available
        if query_cache and config.CACHE_ENABLED:
            query_cache.clear()
            print(f"🗑️  [UPLOAD] Query cache cleared for new content")
        
        print(f"✨ [UPLOAD] Paper upload completed successfully: {paper.title}\n")
        
        return PaperUploadResponse(
            paper_id=paper.id,
            title=paper.title,
            filename=paper.filename,
            total_pages=paper.total_pages,
            chunk_count=paper.chunk_count,
            message="Paper uploaded and processed successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Mark as failed
        if 'paper' in locals():
            paper.processed = -1
            db.commit()
        
        # Provide helpful error messages for common issues
        error_msg = str(e).lower()
        if "connection" in error_msg or "qdrant" in error_msg:
            raise HTTPException(
                status_code=503,
                detail=f"Vector database connection error. Please ensure Qdrant is running on {config.QDRANT_HOST}:{config.QDRANT_PORT}"
            )
        elif "out of memory" in error_msg or "memory" in error_msg:
            raise HTTPException(
                status_code=507,
                detail="Insufficient memory to process this paper. Try a smaller file or restart the service."
            )
        else:
            raise HTTPException(status_code=500, detail=f"Error processing paper: {str(e)}")
    
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass


@router.post("/api/query", response_model=QueryResponse)
async def query_papers(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Query research papers using RAG with caching
    
    - Checks cache for repeated queries (instant response)
    - Retrieves relevant chunks using vector similarity
    - Generates answer using Gemini
    - Returns answer with citations
    - Caches result for future queries
    """
    print(f"\n🔍 [QUERY] Received question: \"{request.question[:100]}...\"")
    print(f"   top_k={request.top_k}, paper_ids={request.paper_ids}")
    
    try:
        # Check cache first (if enabled)
        cache_hit = False
        if query_cache and config.CACHE_ENABLED:
            print(f"💾 [QUERY] Checking cache...")
            cached_result = query_cache.get(
                question=request.question,
                top_k=request.top_k,
                paper_ids=request.paper_ids
            )
            
            if cached_result:
                cache_hit = True
                result = cached_result
                # Add cache indicator to response
                result['cached'] = True
                result['response_time'] = 0.001  # Near-instant from cache
                print(f"⚡ [QUERY] Cache HIT! Returning cached result instantly")
        
        # Cache miss - run RAG pipeline
        if not cache_hit:
            print(f"🔄 [QUERY] Cache MISS - Running full RAG pipeline...")
            result = rag_pipeline.query(
                question=request.question,
                top_k=request.top_k,
                paper_ids=request.paper_ids
            )
            result['cached'] = False
            
            # Cache the result for future queries
            if query_cache and config.CACHE_ENABLED:
                query_cache.set(
                    question=request.question,
                    response=result,
                    top_k=request.top_k,
                    paper_ids=request.paper_ids
                )
        
        # Save query to database (even for cache hits to track usage)
        query_record = QueryModel(
            question=request.question,
            answer=result['answer'],
            paper_ids_filter=request.paper_ids,
            top_k=request.top_k,
            response_time=result['response_time'],
            confidence=result['confidence'],
            sources_used=result['sources_used'],
            citations=result['citations']
        )
        db.add(query_record)
        db.commit()
        print(f"📝 [QUERY] Query saved to history\n")
        
        return QueryResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        # Provide helpful error messages for common issues
        error_msg = str(e).lower()
        if "connection" in error_msg or "qdrant" in error_msg:
            raise HTTPException(
                status_code=503,
                detail=f"Vector database connection error. Please ensure Qdrant is running."
            )
        elif "api" in error_msg and ("key" in error_msg or "auth" in error_msg):
            raise HTTPException(
                status_code=401,
                detail="LLM API authentication error. Please check your GEMINI_API_KEY in .env file."
            )
        elif "rate" in error_msg or "quota" in error_msg:
            raise HTTPException(
                status_code=429,
                detail="API rate limit exceeded. Please wait a moment before trying again."
            )
        elif "no papers" in error_msg or "no documents" in error_msg:
            raise HTTPException(
                status_code=404,
                detail="No papers found in the database. Please upload papers first."
            )
        else:
            raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.get("/api/papers", response_model=List[PaperDetail])
async def list_papers(
    skip: int = QueryParam(0, ge=0),
    limit: int = QueryParam(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all uploaded papers"""
    try:
        papers = db.query(Paper).filter(Paper.processed == 1).offset(skip).limit(limit).all()
        return papers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving papers: {str(e)}")


@router.get("/api/papers/{paper_id}", response_model=PaperDetail)
async def get_paper(paper_id: int, db: Session = Depends(get_db)):
    """Get details of a specific paper"""
    try:
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper with ID {paper_id} not found")
        return paper
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving paper: {str(e)}")


@router.delete("/api/papers/{paper_id}")
async def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    """Delete a paper and its vectors"""
    print(f"\n🗑️  [DELETE] Deleting paper ID: {paper_id}")
    
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        print(f"❌ [DELETE] Paper not found: {paper_id}")
        raise HTTPException(status_code=404, detail=f"Paper with ID {paper_id} not found")
    
    print(f"   Title: {paper.title}")
    
    try:
        # Delete from Qdrant vector database
        print(f"🗄️  [DELETE] Removing vectors from Qdrant...")
        qdrant_service.delete_by_paper_id(paper_id)
        
        # Delete file if exists
        if paper.file_path and os.path.exists(paper.file_path):
            try:
                os.remove(paper.file_path)
            except Exception as file_error:
                # Log but don't fail if file deletion fails
                print(f"Warning: Could not delete file {paper.file_path}: {file_error}")
        
        # Invalidate cached queries for this paper
        if query_cache and config.CACHE_ENABLED:
            query_cache.invalidate_by_paper(paper_id)
            print(f"💾 [DELETE] Invalidated cached queries for paper {paper_id}")
        
        # Delete from database
        db.delete(paper)
        db.commit()
        print(f"✅ [DELETE] Paper '{paper.title}' deleted successfully\n")
        
        return {
            "success": True,
            "message": f"Paper '{paper.title}' deleted successfully",
            "paper_id": paper_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting paper: {str(e)}")


@router.get("/api/papers/{paper_id}/stats", response_model=PaperStats)
async def get_paper_stats(paper_id: int, db: Session = Depends(get_db)):
    """Get statistics for a specific paper"""
    try:
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper with ID {paper_id} not found")
        
        # Get queries that referenced this paper
        queries = db.query(QueryModel).filter(
            QueryModel.paper_ids_filter.contains([paper_id])
        ).all()
        
        total_queries = len(queries)
        avg_confidence = sum(q.confidence for q in queries) / total_queries if total_queries > 0 else 0.0
        
        # Extract common topics (simplified)
        most_common_topics = ["methodology", "results", "datasets"]  # Placeholder
        
        return PaperStats(
            paper_id=paper.id,
            title=paper.title,
            total_queries=total_queries,
            avg_confidence=round(avg_confidence, 3),
            most_common_topics=most_common_topics
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving paper statistics: {str(e)}")


@router.get("/api/queries/history", response_model=List[QueryHistory])
async def get_query_history(
    skip: int = QueryParam(0, ge=0),
    limit: int = QueryParam(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get recent query history"""
    try:
        queries = db.query(QueryModel).order_by(
            QueryModel.query_date.desc()
        ).offset(skip).limit(limit).all()
        
        return queries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving query history: {str(e)}")


@router.get("/api/analytics/popular")
async def get_popular_topics(
    limit: int = QueryParam(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get most queried topics"""
    try:
        # Get all queries
        queries = db.query(QueryModel).all()
        
        if not queries:
            return {
                "popular_topics": [],
                "total_queries": 0,
                "message": "No queries found yet"
            }
        
        # Count word frequency in questions (simplified)
        word_freq = {}
        stop_words = {'what', 'is', 'the', 'how', 'in', 'a', 'an', 'of', 'to', 'and', 'for'}
        
        for query in queries:
            words = query.question.lower().split()
            for word in words:
                if len(word) > 3 and word not in stop_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        popular = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return {
            "popular_topics": [{"topic": word, "count": count} for word, count in popular],
            "total_queries": len(queries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        services_status = {
            "pdf_processor": pdf_processor is not None,
            "embedding_service": embedding_service is not None,
            "qdrant": qdrant_service is not None,
            "rag_pipeline": rag_pipeline is not None,
            "query_cache": query_cache is not None and config.CACHE_ENABLED
        }
        
        # Check if all critical services are running
        all_healthy = all([
            services_status["pdf_processor"],
            services_status["embedding_service"],
            services_status["qdrant"],
            services_status["rag_pipeline"]
        ])
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "services": services_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/api/cache/stats")
async def get_cache_stats():
    """Get cache statistics and performance metrics"""
    try:
        if not query_cache or not config.CACHE_ENABLED:
            return {
                "enabled": False,
                "message": "Cache is disabled. Set CACHE_ENABLED=true in .env to enable caching."
            }
        
        stats = query_cache.get_stats()
        stats['enabled'] = True
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving cache statistics: {str(e)}")


@router.post("/api/cache/clear")
async def clear_cache():
    """Clear all cached queries"""
    try:
        if not query_cache or not config.CACHE_ENABLED:
            raise HTTPException(
                status_code=400,
                detail="Cache is disabled. Set CACHE_ENABLED=true in .env to enable caching."
            )
        
        query_cache.clear()
        return {
            "success": True,
            "message": "Cache cleared successfully",
            "enabled": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@router.post("/api/cache/cleanup")
async def cleanup_expired_cache():
    """Remove expired entries from cache"""
    try:
        if not query_cache or not config.CACHE_ENABLED:
            raise HTTPException(
                status_code=400,
                detail="Cache is disabled. Set CACHE_ENABLED=true in .env to enable caching."
            )
        
        removed_count = query_cache.cleanup_expired()
        return {
            "success": True,
            "message": f"Removed {removed_count} expired entries" if removed_count > 0 else "No expired entries to remove",
            "removed_count": removed_count,
            "enabled": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up cache: {str(e)}")
