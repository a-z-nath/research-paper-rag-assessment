"""
API Routes for Research Paper RAG System

This module contains all the API endpoints for:
- Paper upload and processing
- Paper management (list, get, delete)
- Paper statistics and analytics
"""

import logging
import os
import uuid
import tempfile
from pathlib import Path
from typing import List, Optional
import time

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Local imports
from src.database import get_database_session
from src.models.paper import Paper
from src.models.paper_stats import PaperStats
from src.models.chunk import Chunk
from src.schemas.paper import PaperResponse, PaperListResponse, PaperUploadResponse
from src.schemas.upload import UploadStatus, BatchUploadResponse, FileUploadResult
from src.services.pdf_processor import PDFProcessor
from src.services.text_chunker import TextChunker
from src.services.embedding_service import EmbeddingService
from src.services.qdrant_client import QdrantClientService, StorageRequest
from src.services.batch_processor import BatchProcessor

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
pdf_processor = PDFProcessor()
text_chunker = TextChunker()
embedding_service = EmbeddingService()
qdrant_client = QdrantClientService()

# Initialize batch processor
batch_processor = BatchProcessor(
    upload_dir="uploads",
    collection_name="research_papers",
    max_concurrent_files=5
)

@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        dict: Simple success status
    """
    return {"success": True}


@router.post("/papers/upload", response_model=BatchUploadResponse)
async def upload_papers(
    files: List[UploadFile] = File(...),
    session: Session = Depends(get_database_session)
):
    """
    Upload and process research paper PDFs (supports single or multiple files).
    
    This endpoint:
    1. Accepts single or multiple PDF files
    2. Saves them to the /uploads folder
    3. Extracts content and sections from each PDF
    4. Creates semantic chunks with section metadata
    5. Generates embeddings for all chunks
    6. Stores vectors in Qdrant with paper and section information
    7. Saves paper metadata to database
    
    Args:
        files: Single PDF file or list of PDF files to upload
        session: Database session
    
    Returns:
        BatchUploadResponse: Detailed results for each file processed
    """
    start_time = time.time()
    
    logger.info(f"Starting upload for {len(files)} file(s)")
    
    # Validate all files first
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="All files must have filenames")
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} is not a PDF. Only PDF files are supported"
            )
        
        if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit per file
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} exceeds 50MB limit"
            )
    
    try:
        # Process all files through the batch processor
        results = await batch_processor.process_files(files, session)
        
        # Calculate summary statistics
        successful_uploads = sum(1 for r in results if r.success)
        failed_uploads = len(results) - successful_uploads
        total_processing_time = time.time() - start_time
        
        collection_name = batch_processor.get_collection_name()
        
        # Prepare response
        overall_success = successful_uploads > 0  # Success if at least one file processed
        
        if failed_uploads == 0:
            message = f"All {successful_uploads} file(s) processed successfully"
        elif successful_uploads == 0:
            message = f"All {failed_uploads} file(s) failed to process"
        else:
            message = f"{successful_uploads} file(s) processed successfully, {failed_uploads} failed"
        
        logger.info(f"Upload completed: {message} in {total_processing_time:.2f}s")
        
        return BatchUploadResponse(
            success=overall_success,
            message=message,
            collection_name=collection_name,
            total_files=len(files),
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            uploaded_papers=results,
            total_processing_time=total_processing_time
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        
        # Return error response with what we know
        return BatchUploadResponse(
            success=False,
            message=f"Upload failed: {str(e)}",
            collection_name=batch_processor.get_collection_name(),
            total_files=len(files),
            successful_uploads=0,
            failed_uploads=len(files),
            uploaded_papers=[
                FileUploadResult(
                    file_name=file.filename or f"file_{i}",
                    success=False,
                    message="Failed due to processing error",
                    error_details=str(e)
                ) for i, file in enumerate(files)
            ],
            total_processing_time=time.time() - start_time
        )


@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None,
    session: Session = Depends(get_database_session)
):
    """
    List all papers with pagination and filtering.
    
    Args:
        page: Page number (1-based)
        limit: Number of papers per page
        status: Filter by status (processing, completed, failed)
        session: Database session
    
    Returns:
        PaperListResponse: List of papers with metadata
    """
    try:
        # Build query
        query = session.query(Paper)
        
        if status:
            query = query.filter(Paper.status == status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        papers = query.offset(offset).limit(limit).all()
        
        # Convert to response format
        paper_responses = []
        for paper in papers:
            paper_responses.append(PaperResponse(
                id=str(paper.id),
                title=paper.title,
                authors=paper.authors,
                year=paper.year,
                file_name=paper.file_name,
                num_pages=paper.num_pages,
                uploaded_at=paper.uploaded_at,
                status=paper.status
            ))
        
        return PaperListResponse(
            success=True,
            papers=paper_responses,
            total=total,
            page=page,
            limit=limit,
            total_pages=(total + limit - 1) // limit
        )
        
    except Exception as e:
        logger.error(f"Failed to list papers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve papers")

@router.get("/papers/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    session: Session = Depends(get_database_session)
):
    """
    Get detailed information about a specific paper.
    
    Args:
        paper_id: Paper UUID
        session: Database session
    
    Returns:
        PaperResponse: Paper details
    """
    try:
        paper = session.query(Paper).filter(Paper.id == paper_id).first()
        
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Update view count in paper stats
        stats = session.query(PaperStats).filter(PaperStats.paper_id == paper_id).first()
        if stats:
            stats.views_count = (stats.views_count or 0) + 1
        else:
            # Create stats record if it doesn't exist
            stats = PaperStats(paper_id=paper.id, views_count=1)
            session.add(stats)
        
        session.commit()
        
        return PaperResponse(
            id=str(paper.id),
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            file_name=paper.file_name,
            num_pages=paper.num_pages,
            uploaded_at=paper.uploaded_at,
            status=paper.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get paper {paper_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve paper")

@router.delete("/papers/{paper_id}")
async def delete_paper(
    paper_id: str,
    session: Session = Depends(get_database_session)
):
    """
    Delete a paper and all associated data.
    
    Args:
        paper_id: Paper UUID
        session: Database session
    
    Returns:
        dict: Deletion status
    """
    try:
        paper = session.query(Paper).filter(Paper.id == paper_id).first()
        
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Delete associated chunks
        chunks = session.query(Chunk).filter(Chunk.paper_id == paper_id).all()
        chunk_ids = [chunk.qdrant_id for chunk in chunks]
        
        # Delete from Qdrant
        if chunk_ids:
            await qdrant_client.delete_vectors("papers", chunk_ids)
        
        # Delete from database
        session.query(Chunk).filter(Chunk.paper_id == paper_id).delete()
        session.query(PaperStats).filter(PaperStats.paper_id == paper_id).delete()
        session.delete(paper)
        session.commit()
        
        logger.info(f"Deleted paper {paper_id} and {len(chunk_ids)} chunks")
        
        return {
            "success": True,
            "message": f"Paper {paper_id} deleted successfully",
            "chunks_deleted": len(chunk_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete paper {paper_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete paper")

@router.get("/papers/{paper_id}/stats")
async def get_paper_stats(
    paper_id: str,
    session: Session = Depends(get_database_session)
):
    """
    Get statistics for a specific paper.
    
    Args:
        paper_id: Paper UUID
        session: Database session
    
    Returns:
        dict: Paper statistics
    """
    try:
        paper = session.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        stats = session.query(PaperStats).filter(PaperStats.paper_id == paper_id).first()
        chunk_count = session.query(Chunk).filter(Chunk.paper_id == paper_id).count()
        
        return {
            "success": True,
            "paper_id": paper_id,
            "title": paper.title,
            "status": paper.status,
            "num_pages": paper.num_pages,
            "chunk_count": chunk_count,
            "views_count": stats.views_count if stats else 0,
            "queries_count": stats.queries_count if stats else 0,
            "uploaded_at": paper.uploaded_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get paper stats {paper_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve paper statistics")