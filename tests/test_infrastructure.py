#!/usr/bin/env python3
"""
Infrastructure testing script to verify Qdrant, Ollama, and PostgreSQL connections
"""
import pytest
import asyncio
import os
from dotenv import load_dotenv
import httpx
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import psycopg2
import requests

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_qdrant():
    """Test Qdrant vector database connection and basic operations"""
    
    # Initialize client
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )
    
    # Test basic connection
    collections = client.get_collections()
    assert collections is not None, "Should be able to get collections"
    
    # Test creating a test collection
    test_collection_name = "test_collection"
    
    # Delete if exists
    try:
        client.delete_collection(test_collection_name)
    except:
        pass
    
    # Create test collection
    client.create_collection(
        collection_name=test_collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    
    # Test inserting a vector
    test_vector = [0.1] * 384  # 384-dimensional test vector
    client.upsert(
        collection_name=test_collection_name,
        points=[{
            "id": 1,
            "vector": test_vector,
            "payload": {"text": "test document", "section": "test"}
        }]
    )
    
    # Test searching
    search_results = client.search(
        collection_name=test_collection_name,
        query_vector=test_vector,
        limit=1
    )
    
    assert len(search_results) > 0, "Should find at least one result"
    
    # Cleanup
    client.delete_collection(test_collection_name)

def test_postgresql():
    """Test PostgreSQL database connection"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not found in environment variables")
    
    # Connect to database
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    # Test basic query
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    assert version is not None, "Should get database version"
    assert "PostgreSQL" in version[0], "Should be PostgreSQL database"
    
    # Test creating a test table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Test insert
    cursor.execute(
        "INSERT INTO test_table (name) VALUES (%s) RETURNING id;",
        ("test_entry",)
    )
    test_id = cursor.fetchone()[0]
    assert test_id is not None, "Should get inserted ID"
    
    # Test select
    cursor.execute("SELECT COUNT(*) FROM test_table;")
    count = cursor.fetchone()[0]
    assert count > 0, "Should have at least one record"
    
    # Cleanup
    cursor.execute("DROP TABLE IF EXISTS test_table;")
    conn.commit()
    
    cursor.close()
    conn.close()

@pytest.mark.asyncio
async def test_ollama():
    """Test Ollama LLM service connection"""
    
    # Check if using cloud or local Ollama
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    api_key = os.getenv("OLLAMA_API_KEY")
    model = os.getenv("OLLAMA_MODEL", "llama3")
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    # Test basic connection
    async with httpx.AsyncClient(timeout=30.0) as client:
        # For cloud Ollama, test the API endpoint
        if "ollama.com" in base_url:
            # Test with a simple generation request
            response = await client.post(
                f"{base_url}/api/generate",
                headers=headers,
                json={
                    "model": model,
                    "prompt": "Hello, respond with just 'Hi there!'",
                    "stream": False
                }
            )
        else:
            # For local Ollama, test the health endpoint first
            health_response = await client.get(f"{base_url}/api/tags")
            assert health_response.status_code == 200, "Ollama service should be running"
            
            # Test generation
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "Hello, respond with just 'Hi there!'",
                    "stream": False
                }
            )
        
        assert response.status_code == 200, f"Ollama generation failed: {response.status_code} - {response.text}"
        
        result = response.json()
        generated_text = result.get("response", "No response")
        assert len(generated_text) > 0, "Should generate some text"

# Note: This file now uses pytest format
# Run with: python -m pytest tests/test_infrastructure.py -v