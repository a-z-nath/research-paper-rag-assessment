"""
Batch Processing Service for Multiple File Uploads

Handles the orchestration of processing multiple PDF files through the
complete ingestion pipeline with error handling and progress tracking.
"""

import os
import time
import logging
import asyncio
import uuid
from pathlib import Path
from typing import List, Dict, Any
from fastapi import UploadFile
from sqlalchemy.orm import Session

from src.database import get_database_session
from src.models.paper import Paper
from src.models.paper_stats import PaperStats
from src.models.chunk import Chunk
from src.services.pdf_processor import PDFProcessor
from src.services.text_chunker import TextChunker
from src.services.embedding_service import EmbeddingService
from src.services.qdrant_client import QdrantClientService, StorageRequest
from src.schemas.upload import FileUploadResult

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Handles batch processing of multiple PDF files through the complete pipeline
    """
    
    def __init__(
        self,
        upload_dir: str = "uploads",
        collection_name: str = "research_papers",
        max_concurrent_files: int = 3
    ):
        self.upload_dir = Path(upload_dir)
        self.collection_name = collection_name
        self.max_concurrent_files = max_concurrent_files
        
        # Ensure upload directory exists
        self.upload_dir.mkdir(exist_ok=True)
        
        # Initialize services
        self.pdf_processor = PDFProcessor()
        self.text_chunker = TextChunker()
        self.embedding_service = EmbeddingService()
        self.qdrant_client = QdrantClientService(collection_name=collection_name, host="localhost", port=6333)
        
        logger.info(f"BatchProcessor initialized with upload_dir={upload_dir}")

    async def process_files(
        self, 
        files: List[UploadFile], 
    ) -> List[FileUploadResult]:
        """
        Process multiple files through the complete pipeline
        
        Args:
            files: List of uploaded files
            
        Returns:
            List of processing results for each file
        """
        logger.info(f"Starting batch processing of {len(files)} files")
        
        # Ensure Qdrant collection exists
        await self.qdrant_client.ensure_collection_exists(self.collection_name)
        
        db_session = get_database_session()
        
        # Process files with concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_files)
        tasks = [
            self._process_single_file(file, db_session, semaphore)
            for file in files
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions from tasks
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} failed with exception: {str(result)}")
                processed_results.append(
                    FileUploadResult(
                        file_name=files[i].filename or f"file_{i}",
                        success=False,
                        message="Processing failed with exception",
                        error_details=str(result)
                    )
                )
            else:
                processed_results.append(result)
        
        logger.info(f"Batch processing completed. {sum(1 for r in processed_results if r.success)} successful, {sum(1 for r in processed_results if not r.success)} failed")
        return processed_results

    async def _process_single_file(
        self,
        file: UploadFile,
        db_session: Session,
        semaphore: asyncio.Semaphore
    ) -> FileUploadResult:
        """
        Process a single file through the complete pipeline
        
        Args:
            file: Uploaded file
            db_session: Database session
            semaphore: Concurrency control
            
        Returns:
            Processing result for the file
        """
        async with semaphore:
            start_time = time.time()
            file_name = file.filename or "unknown_file.pdf"
            
            logger.info(f"Processing file: {file_name}")
            
            try:
                # 1. Save file to uploads directory
                file_path = await self._save_uploaded_file(file)
                
                # 2. Extract PDF content
                pdf_result = self.pdf_processor.process_pdf(str(file_path))
                if not pdf_result.sections:
                    return FileUploadResult(
                        file_name=file_name,
                        success=False,
                        message="No content could be extracted from PDF",
                        file_path=str(file_path)
                    )
                
                # 3. Create paper record in database
                paper = Paper(
                    title=pdf_result.metadata.title or file_path.stem,
                    authors=pdf_result.metadata.authors,
                    year=pdf_result.metadata.year,
                    file_name=file_name,
                    file_path=str(file_path),
                    full_text=pdf_result.full_text,  # Store the complete extracted text
                    num_pages=pdf_result.metadata.num_pages
                )
                db_session.add(paper)
                db_session.commit()
                db_session.refresh(paper)
                
                # 4. Create paper stats
                stats = PaperStats(paper_id=paper.id)
                db_session.add(stats)
                db_session.commit()
                
                # 5. Chunk text by sections
                chunking_result = self.text_chunker.chunk_pdf_content(pdf_result)
                if not chunking_result.chunks:
                    return FileUploadResult(
                        file_name=file_name,
                        success=False,
                        message="No chunks could be created from PDF content",
                        paper_id=str(paper.id),
                        file_path=str(file_path)
                    )
                
                # 6. Generate embeddings
                chunk_dicts = [chunk.to_dict() for chunk in chunking_result.chunks]
                enriched_chunks = self.embedding_service.encode_chunks(chunk_dicts)
                
                # 7. Store in Qdrant
                await self._store_vectors_in_qdrant(enriched_chunks, paper, db_session)
                
                processing_time = time.time() - start_time
                
                logger.info(f"Successfully processed {file_name} in {processing_time:.2f}s")
                
                return FileUploadResult(
                    file_name=file_name,
                    success=True,
                    message="File processed successfully",
                    paper_id=str(paper.id),
                    title=paper.title,
                    authors=paper.authors,
                    year=paper.year,
                    num_pages=paper.num_pages,
                    chunks_created=len(enriched_chunks),
                    file_path=str(file_path),
                    processing_time=processing_time
                )
                
            except Exception as e:
                logger.error(f"Failed to process {file_name}: {str(e)}", exc_info=True)
                
                # Cleanup on error
                try:
                    if 'paper' in locals():
                        db_session.delete(paper)
                        db_session.commit()
                except:
                    db_session.rollback()
                
                return FileUploadResult(
                    file_name=file_name,
                    success=False,
                    message=f"Processing failed: {str(e)}",
                    error_details=str(e),
                    processing_time=time.time() - start_time
                )

    async def _save_uploaded_file(self, file: UploadFile) -> Path:
        """
        Save uploaded file to the uploads directory
        
        Args:
            file: Uploaded file
            
        Returns:
            Path to saved file
        """
        # Generate unique filename to avoid conflicts
        timestamp = int(time.time() * 1000)
        file_name = file.filename or "uploaded_file.pdf"
        name_parts = file_name.rsplit('.', 1)
        if len(name_parts) == 2:
            unique_name = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
        else:
            unique_name = f"{file_name}_{timestamp}"
        
        file_path = self.upload_dir / unique_name
        
        # Save file content
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Reset file position for potential reuse
        await file.seek(0)
        
        logger.info(f"Saved file to: {file_path}")
        return file_path

    async def _store_vectors_in_qdrant(
        self,
        enriched_chunks: List[Dict[str, Any]],
        paper: Paper,
        db_session: Session
    ) -> None:
        """
        Store vectors and metadata in Qdrant and chunk records in database
        
        Args:
            enriched_chunks: Chunks with embeddings
            paper: Paper database record
            db_session: Database session
        """
        vectors = [chunk['embedding'] for chunk in enriched_chunks]
        payloads = []
        chunk_records = []
        qdrant_ids = []
        
        for i, chunk in enumerate(enriched_chunks):
            # Generate UUID for Qdrant (required format)
            qdrant_id = str(uuid.uuid4())
            qdrant_ids.append(qdrant_id)
            
            # Prepare Qdrant payload with comprehensive metadata
            payload = {
                "paper_id": str(paper.id),
                "paper_title": paper.title,
                "paper_authors": paper.authors,
                "paper_year": paper.year,
                "section_name": chunk['section_name'],
                "section_type": chunk['section_type'],
                "chunk_index": chunk['chunk_index'],
                "content_preview": chunk['content'][:200],
                "content": chunk['content'],
                "file_name": paper.file_name,
                "uploaded_at": time.time()
            }
            payloads.append(payload)
            
            # Prepare database chunk record with the same UUID
            chunk_record = Chunk(
                paper_id=paper.id,
                section=chunk['section_name'],
                chunk_index=chunk['chunk_index'],
                snippet=chunk['content'],
                qdrant_id=qdrant_id
            )
            chunk_records.append(chunk_record)
        
        # Store vectors in Qdrant with UUIDs
        storage_request = StorageRequest(
            vectors=vectors,
            payloads=payloads,
            ids=qdrant_ids,  # Use the same UUIDs we stored in chunk records
            collection_name=self.collection_name
        )
        
        success = await self.qdrant_client.store_vectors(storage_request)
        if not success:
            raise RuntimeError("Failed to store vectors in Qdrant")
        
        # Store chunk metadata in database
        db_session.add_all(chunk_records)
        db_session.commit()
        
        logger.info(f"Stored {len(vectors)} vectors for paper {paper.id}")

    def get_collection_name(self) -> str:
        """Get the collection name being used"""
        return self.collection_name

    async def cleanup_failed_uploads(self, file_paths: List[str]) -> None:
        """
        Cleanup files from failed uploads
        
        Args:
            file_paths: List of file paths to cleanup
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup file {file_path}: {str(e)}")