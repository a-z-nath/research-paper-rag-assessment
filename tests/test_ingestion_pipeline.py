#!/usr/bin/env python3
"""
Complete Ingestion Pipeline Test

Tests the end-to-end workflow:
PDF → PDF Processor → Text Chunker → Embedding Service → Qdrant Storage → PostgreSQL Metadata

This test validates the entire paper processing pipeline that will be used
in the production RAG system.
"""
import pytest
import sys
import os
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.pdf_processor import PDFProcessor
from src.services.text_chunker import TextChunker
from src.services.embedding_service import EmbeddingService
from src.services.qdrant_client import QdrantClientService, StorageRequest, SearchRequest
from src.database import get_database_session, create_tables
from src.models import Paper, Chunk, PaperStats

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_qdrant_client_basic(qdrant_client):
    """Test basic Qdrant client functionality"""
    
    # Test connection
    connection_test = await qdrant_client.test_connection()
    
    assert connection_test["success"], f"Qdrant connection failed: {connection_test.get('error', '')}"
    assert connection_test['connection_time'] > 0, "Connection should take some time"
    assert connection_test['storage_time'] > 0, "Storage should take some time"
    assert connection_test['search_time'] > 0, "Search should take some time"
    assert connection_test['collections_count'] >= 0, "Should report collections count"

@pytest.mark.asyncio
async def test_complete_ingestion_pipeline(pdf_processor, text_chunker, embedding_service, sample_papers_dir):
    """Test the complete end-to-end ingestion pipeline"""
    
    # Initialize Qdrant client for this test
    qdrant_client = QdrantClientService(
        collection_name="test_ingestion",
        embedding_dim=384
    )
    
    # Check for sample PDFs
    if not sample_papers_dir.exists():
        pytest.skip("sample_papers directory not found")
    
    pdf_files = list(sample_papers_dir.glob("*.pdf"))
    if not pdf_files:
        pytest.skip("No PDF files found in sample_papers")
    
    # Test with first PDF file
    test_file = pdf_files[0]
    
    # Get database session
    session = get_database_session()
    
    try:
        pipeline_start = time.time()
        
        # Step 1: Process PDF
        pdf_result = pdf_processor.process_pdf(str(test_file))
        assert len(pdf_result.sections) > 0, "Should extract at least one section"
        assert pdf_result.metadata.num_pages > 0, "Should have page count"
        
        # Step 2: Create database record
        paper = Paper(
            title=pdf_result.metadata.title or test_file.stem,
            authors=pdf_result.metadata.authors,
            year=pdf_result.metadata.year,
            file_name=test_file.name,
            file_path=str(test_file),
            num_pages=pdf_result.metadata.num_pages
        )
        session.add(paper)
        session.commit()
        
        # Create paper stats
        stats = PaperStats(paper_id=paper.id)
        session.add(stats)
        session.commit()
        
        # Step 3: Text Chunking
        chunking_result = text_chunker.chunk_pdf_content(pdf_result)
        assert chunking_result.total_chunks > 0, "Should create at least one chunk"
        assert chunking_result.total_tokens > 0, "Should have token count"
        
        # Step 4: Generate Embeddings
        chunk_dicts = [chunk.to_dict() for chunk in chunking_result.chunks]
        enriched_chunks = embedding_service.encode_chunks(chunk_dicts)
        assert len(enriched_chunks) == len(chunk_dicts), "Should enrich all chunks"
        
        # Step 5: Store in Qdrant
        vectors = [chunk['embedding'] for chunk in enriched_chunks]
        payloads = []
        chunk_records = []
        
        for i, chunk in enumerate(enriched_chunks):
            # Prepare Qdrant payload
            qdrant_id = f"chunk_{paper.id}_{i}"
            payload = {
                "paper_id": str(paper.id),
                "paper_title": paper.title,
                "section_name": chunk['section_name'],
                "section_type": chunk['section_type'],
                "chunk_index": chunk['chunk_index'],
                "content_preview": chunk['content'][:200]
            }
            payloads.append(payload)
            
            # Prepare database chunk record
            chunk_record = Chunk(
                paper_id=paper.id,
                section=chunk['section_name'],
                chunk_index=chunk['chunk_index'],
                snippet=chunk['content'],
                qdrant_id=qdrant_id
            )
            chunk_records.append(chunk_record)
        
        # Store vectors in Qdrant
        storage_request = StorageRequest(
            vectors=vectors,
            payloads=payloads,
            ids=[f"chunk_{paper.id}_{i}" for i in range(len(vectors))],
            collection_name="test_ingestion"
        )
        
        qdrant_success = await qdrant_client.store_vectors(storage_request)
        assert qdrant_success, "Should successfully store vectors in Qdrant"
        
        # Store chunk metadata in database
        session.add_all(chunk_records)
        session.commit()
        
        # Step 6: Test Retrieval
        test_query = "machine learning methodology approach"
        test_embedding = embedding_service.encode_single(test_query)
        
        search_request = SearchRequest(
            query_vector=test_embedding,
            collection_name="test_ingestion",
            top_k=3,
            score_threshold=0.1,
            filter_conditions={"paper_id": str(paper.id)}
        )
        
        search_results = await qdrant_client.search_similar(search_request)
        assert len(search_results) > 0, "Should find at least one result"
        
        if search_results:
            best_result = search_results[0]
            assert 0.0 <= best_result.score <= 1.0, "Score should be between 0 and 1"
            assert 'section_name' in best_result.payload, "Result should have section name"
        
        # Pipeline completion
        total_time = time.time() - pipeline_start
        assert total_time > 0, "Pipeline should take some time"
        
        # Cleanup test data
        session.delete(stats)
        for chunk_record in chunk_records:
            session.delete(chunk_record)
        session.delete(paper)
        session.commit()
        
        await qdrant_client.cleanup_collection("test_ingestion")
        
    except Exception as e:
        # Cleanup on error
        try:
            session.rollback()
            await qdrant_client.cleanup_collection("test_ingestion")
        except:
            pass
        raise e
    
    """Test the complete end-to-end ingestion pipeline"""
    
    # Initialize Qdrant client for this test
    qdrant_client = QdrantClientService(
        collection_name="test_ingestion",
        embedding_dim=384
    )
    
    # Check for sample PDFs
    if not sample_papers_dir.exists():
        pytest.skip("sample_papers directory not found")
    
    pdf_files = list(sample_papers_dir.glob("*.pdf"))
    if not pdf_files:
        pytest.skip("No PDF files found in sample_papers")
    
    # Test with first PDF file
    test_file = pdf_files[0]
    
    # Get database session
    session = get_database_session()
    
    try:
        pipeline_start = time.time()
        
        # Step 1: Process PDF
        pdf_result = pdf_processor.process_pdf(str(test_file))
        assert len(pdf_result.sections) > 0, "Should extract at least one section"
        assert pdf_result.metadata.num_pages > 0, "Should have page count"
        
        # Step 2: Create database record
        paper = Paper(
            title=pdf_result.metadata.title or test_file.stem,
            authors=pdf_result.metadata.authors,
            year=pdf_result.metadata.year,
            file_name=test_file.name,
            file_path=str(test_file),
            num_pages=pdf_result.metadata.num_pages
        )
        session.add(paper)
        session.commit()
        
        # Create paper stats
        stats = PaperStats(paper_id=paper.id)
        session.add(stats)
        session.commit()
        
        # Step 3: Text Chunking
        chunking_result = text_chunker.chunk_pdf_content(pdf_result)
        assert chunking_result.total_chunks > 0, "Should create at least one chunk"
        assert chunking_result.total_tokens > 0, "Should have token count"
        
        # Step 4: Generate Embeddings
        chunk_dicts = [chunk.to_dict() for chunk in chunking_result.chunks]
        enriched_chunks = embedding_service.encode_chunks(chunk_dicts)
        assert len(enriched_chunks) == len(chunk_dicts), "Should enrich all chunks"
        
        # Step 5: Store in Qdrant
        vectors = [chunk['embedding'] for chunk in enriched_chunks]
        payloads = []
        chunk_records = []
        
        for i, chunk in enumerate(enriched_chunks):
            # Prepare Qdrant payload
            qdrant_id = f"chunk_{paper.id}_{i}"
            payload = {
                "paper_id": str(paper.id),
                "paper_title": paper.title,
                "section_name": chunk['section_name'],
                "section_type": chunk['section_type'],
                "chunk_index": chunk['chunk_index'],
                "content_preview": chunk['content'][:200]
            }
            payloads.append(payload)
            
            # Prepare database chunk record
            chunk_record = Chunk(
                paper_id=paper.id,
                section=chunk['section_name'],
                chunk_index=chunk['chunk_index'],
                snippet=chunk['content'],
                qdrant_id=qdrant_id
            )
            chunk_records.append(chunk_record)
        
        # Store vectors in Qdrant
        storage_request = StorageRequest(
            vectors=vectors,
            payloads=payloads,
            ids=[f"chunk_{paper.id}_{i}" for i in range(len(vectors))],
            collection_name="test_ingestion"
        )
        
        qdrant_success = await qdrant_client.store_vectors(storage_request)
        assert qdrant_success, "Should successfully store vectors in Qdrant"
        
        # Store chunk metadata in database
        session.add_all(chunk_records)
        session.commit()
        
        # Step 6: Test Retrieval
        test_query = "machine learning methodology approach"
        test_embedding = embedding_service.encode_single(test_query)
        
        search_request = SearchRequest(
            query_vector=test_embedding,
            collection_name="test_ingestion",
            top_k=3,
            score_threshold=0.1,
            filter_conditions={"paper_id": str(paper.id)}
        )
        
        search_results = await qdrant_client.search_similar(search_request)
        assert len(search_results) > 0, "Should find at least one result"
        
        if search_results:
            best_result = search_results[0]
            assert 0.0 <= best_result.score <= 1.0, "Score should be between 0 and 1"
            assert 'section_name' in best_result.payload, "Result should have section name"
        
        # Pipeline completion
        total_time = time.time() - pipeline_start
        assert total_time > 0, "Pipeline should take some time"
        
        # Cleanup test data
        session.delete(stats)
        for chunk_record in chunk_records:
            session.delete(chunk_record)
        session.delete(paper)
        session.commit()
        
        await qdrant_client.cleanup_collection("test_ingestion")
        
    except Exception as e:
        # Cleanup on error
        try:
            session.rollback()
            await qdrant_client.cleanup_collection("test_ingestion")
        except:
            pass
        raise e
    
    finally:
        session.close()