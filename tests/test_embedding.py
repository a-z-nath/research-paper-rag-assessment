#!/usr/bin/env python3
"""
Test script for Embedding Service using SPECTER model
Tests embedding generation, chunking integration, and performance
"""
import pytest
import sys
import os
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.embedding_service import EmbeddingService
from src.services.pdf_processor import PDFProcessor
from src.services.text_chunker import TextChunker

def test_embedding_service_basic(embedding_service):
    """Test basic embedding service functionality"""
    
    # Test model info
    model_info = embedding_service.get_model_info()
    assert model_info['model_name'] == "all-MiniLM-L6-v2"
    assert model_info['embedding_dim'] == 384
    assert model_info['device'] in ['cpu', 'cuda']
    
    # Test single embedding
    test_text = "This paper presents a novel machine learning approach for natural language processing using transformer architectures."
    
    test_result = embedding_service.test_embedding(test_text)
    assert test_result['success'], f"Single embedding test failed: {test_result.get('error', '')}"
    assert test_result['embedding_shape'] == (384,), "Embedding should have correct shape"
    assert test_result['encoding_time'] > 0, "Encoding should take some time"
    assert test_result['embedding_norm'] > 0, "Embedding should have non-zero norm"
    
    # Test batch embedding
    test_texts = [
        "This research investigates machine learning algorithms for classification tasks.",
        "We propose a new methodology for data preprocessing in neural networks.",
        "The experimental results demonstrate significant improvements over baseline methods.",
        "Our approach shows promising results on multiple benchmark datasets."
    ]
    
    batch_result = embedding_service.encode_texts(test_texts, show_progress=False)
    assert len(batch_result.texts) == len(test_texts), "Should process all texts"
    assert batch_result.embeddings.shape == (len(test_texts), 384), "Should have correct embedding shape"
    assert batch_result.processing_time > 0, "Should take some time to process"
    assert batch_result.model_name == "all-MiniLM-L6-v2", "Should use correct model"
    
    # Test similarity calculation
    emb1 = batch_result.embeddings[0]
    emb2 = batch_result.embeddings[1]
    emb3 = batch_result.embeddings[0]  # Same as emb1
    
    similarity_diff = embedding_service.calculate_similarity(emb1, emb2)
    similarity_same = embedding_service.calculate_similarity(emb1, emb3)
    
    assert 0.0 <= similarity_diff <= 1.0, "Similarity should be between 0 and 1"
    assert 0.0 <= similarity_same <= 1.0, "Similarity should be between 0 and 1"
    assert similarity_same > similarity_diff, "Same text should be more similar than different texts"

def test_chunking_integration(pdf_processor, text_chunker, embedding_service, sample_papers_dir):
    """Test integration between chunking and embedding services"""
    
    # Find a sample PDF
    if not sample_papers_dir.exists():
        pytest.skip("sample_papers directory not found")
    
    pdf_files = list(sample_papers_dir.glob("*.pdf"))
    if not pdf_files:
        pytest.skip("No PDF files found in sample_papers")
    
    # Use first PDF
    test_file = pdf_files[0]
    
    # Step 1: Process PDF
    pdf_result = pdf_processor.process_pdf(str(test_file))
    assert len(pdf_result.sections) > 0, "Should extract at least one section"
    
    # Step 2: Chunk content
    chunking_result = text_chunker.chunk_pdf_content(pdf_result)
    assert chunking_result.total_chunks > 0, "Should create at least one chunk"
    
    # Convert chunks to dictionaries
    chunk_dicts = [chunk.to_dict() for chunk in chunking_result.chunks[:3]]  # Test with first 3 chunks
    
    # Step 3: Add embeddings
    enriched_chunks = embedding_service.encode_chunks(chunk_dicts)
    assert len(enriched_chunks) == len(chunk_dicts), "Should have same number of enriched chunks"
    
    # Verify integration
    sample_chunk = enriched_chunks[0]
    assert 'embedding' in sample_chunk, "Chunk should have embedding"
    assert 'embedding_model' in sample_chunk, "Chunk should have embedding model info"
    assert sample_chunk['embedding'].shape[0] == embedding_service.embedding_dim, "Embedding should have correct dimension"
    
    # Test similarity between chunks
    if len(enriched_chunks) >= 2:
        sim = embedding_service.calculate_similarity(
            enriched_chunks[0]['embedding'],
            enriched_chunks[1]['embedding']
        )
        assert 0.0 <= sim <= 1.0, "Similarity should be between 0 and 1"

def _helper_mock_integration(text_chunker, embedding_service, mock_pdf_result):
    """Helper function for mock integration testing"""
    
    # Test chunking
    chunking_result = text_chunker.chunk_pdf_content(mock_pdf_result)
    assert chunking_result.total_chunks > 0, "Should create chunks from mock data"
    
    # Convert to dictionaries and add embeddings
    chunk_dicts = [chunk.to_dict() for chunk in chunking_result.chunks]
    enriched_chunks = embedding_service.encode_chunks(chunk_dicts)
    assert len(enriched_chunks) == len(chunk_dicts), "Should enrich all chunks"
    
    return enriched_chunks

def test_performance(embedding_service):
    """Test embedding service performance"""
    
    # Test with different batch sizes
    test_texts = [
        f"This is test text number {i} about machine learning and artificial intelligence research."
        for i in range(20)  # Reduced for faster testing
    ]
    
    # Single text performance
    start_time = time.time()
    for text in test_texts[:3]:  # Reduced for faster testing
        embedding_service.encode_single(text)
    single_time = time.time() - start_time
    
    # Batch performance
    start_time = time.time()
    batch_result = embedding_service.encode_texts(test_texts[:3], show_progress=False)
    batch_time = time.time() - start_time
    
    # Performance assertions
    assert single_time > 0, "Single encoding should take some time"
    assert batch_time > 0, "Batch encoding should take some time"
    assert batch_result.embeddings.shape[0] == 3, "Should process 3 texts"
    assert batch_result.embeddings.shape[1] == 384, "Should have correct embedding dimension"
    
    # Larger batch test
    start_time = time.time()
    large_batch_result = embedding_service.encode_texts(test_texts, show_progress=False)
    large_batch_time = time.time() - start_time
    
    assert large_batch_result.embeddings.shape[0] == len(test_texts), "Should process all texts"
    assert large_batch_time > 0, "Large batch should take some time"
    assert len(test_texts)/large_batch_time > 0, "Should have positive throughput"

def test_with_mock_data(text_chunker, embedding_service, mock_pdf_result):
    """Test embedding integration with mock data"""
    
    # Test chunking
    chunking_result = text_chunker.chunk_pdf_content(mock_pdf_result)
    assert chunking_result.total_chunks > 0, "Should create chunks from mock data"
    
    # Convert to dictionaries and add embeddings
    chunk_dicts = [chunk.to_dict() for chunk in chunking_result.chunks]
    enriched_chunks = embedding_service.encode_chunks(chunk_dicts)
    assert len(enriched_chunks) == len(chunk_dicts), "Should enrich all chunks"
    
    # Verify enrichment
    for chunk in enriched_chunks:
        assert 'embedding' in chunk, "Chunk should have embedding"
        assert 'embedding_model' in chunk, "Chunk should have embedding model"
        assert chunk['embedding'].shape[0] == 384, "Embedding should have correct dimension"

# Note: This file now uses pytest format
# Run with: python -m pytest tests/test_embedding.py -v