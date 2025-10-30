"""
Query API Routes for Research Paper RAG System

This module contains the query endpoint for:
- Paper search and retrieval
- RAG-based question answering
- Query history tracking
"""

import logging
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

# Local imports
from src.database import get_database_session
from src.models.paper import Paper
from src.models.paper_stats import PaperStats
from src.models.query import Query
from src.schemas.query import QueryRequest, QueryResponse, Citation
from src.services.rag_pipeline import RAGPipeline
from src.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

settings = get_settings()

# Initialize RAG pipeline
rag_pipeline = RAGPipeline(
    collection_name="research_papers",
    embedding_model="all-MiniLM-L6-v2",  # Fixed typo
    ollama_base_url=settings.OLLAMA_BASE_URL,
    ollama_model=settings.OLLAMA_MODEL,
    ollama_api_key=settings.OLLAMA_API_KEY
)

@router.post("/query", response_model=QueryResponse)
async def query_papers(
    request: QueryRequest,
    session: Session = Depends(get_database_session)
):
    """
    Query research papers using RAG pipeline.
    
    This endpoint:
    1. Generates query embedding from the question
    2. Searches Qdrant for relevant chunks with optional paper filtering
    3. Prepares context from retrieved chunks
    4. Generates answer using Ollama LLM
    5. Stores query history in database
    6. Returns structured response with citations
    
    Args:
        request: Query request with question, top_k, and optional paper filters
        session: Database session
    
    Returns:
        QueryResponse: Answer with citations and metadata
    """
    start_time = time.time()
    query_id = str(uuid.uuid4())
    
    logger.info(f"Processing query: {request.question[:100]}...")
    
    try:
        # Validate paper IDs if provided
        if request.paper_ids:
            existing_papers = session.query(Paper.id).filter(
                Paper.id.in_(request.paper_ids)
            ).all()
            existing_ids = [str(p.id) for p in existing_papers]
            
            if len(existing_ids) != len(request.paper_ids):
                missing_ids = set(request.paper_ids) - set(existing_ids)
                raise HTTPException(
                    status_code=400,
                    detail=f"Papers not found: {list(missing_ids)}"
                )
        
        # Process query through RAG pipeline
        rag_result = await rag_pipeline.process_query(
            question=request.question,
            top_k=request.top_k,
            paper_filters=request.paper_ids
        )
        
        # Extract unique paper IDs from citations
        sourced_paper_used = list(set([
            citation.paper_id for citation in rag_result.citations
        ]))
        
        # Update paper stats for papers that were used in the answer
        for paper_id in sourced_paper_used:
            stats = session.query(PaperStats).filter(
                PaperStats.paper_id == paper_id
            ).first()
            
            if stats:
                stats.queries_count = (stats.queries_count or 0) + 1
            else:
                stats = PaperStats(paper_id=paper_id, queries_count=1)
                session.add(stats)
        
        # Store query history
        processing_time = time.time() - start_time
        
        query_record = Query(
            id=query_id,
            question=request.question,
            answer=rag_result.answer,
            confidence=rag_result.confidence,
            top_k=request.top_k,
            paper_ids=request.paper_ids or [],
            sourced_paper_ids=sourced_paper_used,
            citation_chunk_ids=[c.chunk_id for c in rag_result.citations],
            response_time=processing_time
        )
        
        session.add(query_record)
        session.commit()
        
        logger.info(f"Query processed successfully in {processing_time:.2f}s")
        
        # Prepare response
        return QueryResponse(
            question=request.question,
            answer=rag_result.answer,
            citations=rag_result.citations,
            sourced_paper_used=sourced_paper_used,
            confidence=rag_result.confidence,
            query_id=query_id,
            response_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process query: {str(e)}", exc_info=True)
        # Store failed query for analytics
        try:
            processing_time = time.time() - start_time
            query_record = Query(
                id=query_id,
                question=request.question,
                answer="",
                confidence=0.0,
                top_k=request.top_k,
                paper_ids=request.paper_ids or [],
                sourced_paper_ids=[],
                citation_chunk_ids=[],
                response_time=processing_time,
                error_message=str(e)
            )
            session.add(query_record)
            session.commit()
        except Exception as db_error:
            logger.error(f"Failed to store error query: {str(db_error)}")
        
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")

@router.get("/rag/health")
async def rag_health_check():
    """
    Check RAG pipeline component health.
    
    Returns:
        dict: Health status of RAG components
    """
    try:
        health_status = await rag_pipeline.health_check()
        return health_status
        
    except Exception as e:
        logger.error(f"RAG health check failed: {str(e)}", exc_info=True)
        return {
            "overall_healthy": False,
            "components": {
                "error": {
                    "healthy": False,
                    "message": f"Health check failed: {str(e)}"
                }
            }
        }

@router.get("/queries/history")
async def get_query_history(
    page: int = 1,
    limit: int = 10,
    session: Session = Depends(get_database_session)
):
    """
    Get query history with pagination.
    
    Args:
        page: Page number (1-based)
        limit: Number of queries per page
        session: Database session
    
    Returns:
        dict: Query history with pagination metadata
    """
    try:
        # Get total count
        total = session.query(Query).count()
        
        # Apply pagination
        offset = (page - 1) * limit
        queries = session.query(Query).order_by(
            Query.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        # Convert to response format
        query_responses = []
        for query in queries:
            query_responses.append({
                "query_id": str(query.id),
                "question": query.question,
                "answer": query.answer,
                "confidence": query.confidence,
                "response_time": query.response_time,
                "created_at": query.created_at,
                "sourced_papers_count": len(query.sourced_paper_ids or []),
                "citations_count": len(query.citation_chunk_ids or [])
            })
        
        return {
            "success": True,
            "queries": query_responses,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get query history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve query history")

@router.get("/analytics/popular")
async def get_popular_analytics(
    session: Session = Depends(get_database_session)
):
    """
    Get analytics about popular papers and queries.
    
    Args:
        session: Database session
    
    Returns:
        dict: Analytics data
    """
    try:
        # Most queried papers
        popular_papers = session.query(
            Paper.id,
            Paper.title,
            PaperStats.queries_count
        ).join(PaperStats, Paper.id == PaperStats.paper_id).filter(
            PaperStats.queries_count > 0
        ).order_by(PaperStats.queries_count.desc()).limit(10).all()
        
        # Most viewed papers
        popular_views = session.query(
            Paper.id,
            Paper.title,
            PaperStats.views_count
        ).join(PaperStats, Paper.id == PaperStats.paper_id).filter(
            PaperStats.views_count > 0
        ).order_by(PaperStats.views_count.desc()).limit(10).all()
        
        # Recent query trends
        recent_queries = session.query(Query).order_by(
            Query.created_at.desc()
        ).limit(5).all()
        
        return {
            "success": True,
            "popular_papers_by_queries": [
                {
                    "paper_id": str(p.id),
                    "title": p.title,
                    "query_count": p.queries_count
                }
                for p in popular_papers
            ],
            "popular_papers_by_views": [
                {
                    "paper_id": str(p.id),
                    "title": p.title,
                    "view_count": p.views_count
                }
                for p in popular_views
            ],
            "recent_queries": [
                {
                    "question": q.question[:100] + "..." if len(q.question) > 100 else q.question,
                    "confidence": q.confidence,
                    "created_at": q.created_at
                }
                for q in recent_queries
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")