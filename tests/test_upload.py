#!/usr/bin/env python3
"""
Debug script to test upload process step by step
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.embedding_service import EmbeddingService
from src.services.qdrant_client import QdrantClientService, StorageRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_qdrant_connection():
    """Test Qdrant connection and storage"""
    print("🔍 Testing Qdrant connection...")
    
    # Initialize services
    qdrant_client = QdrantClientService(collection_name="test_collection")
    embedding_service = EmbeddingService()
    
    try:
        # Test 1: Ensure collection exists
        print("1. Testing collection creation...")
        success = await qdrant_client.ensure_collection_exists("test_collection")
        print(f"   Collection creation: {'✅ Success' if success else '❌ Failed'}")
        
        if not success:
            return False
        
        # Test 2: Create some test embeddings
        print("2. Testing embedding generation...")
        test_texts = [
            "This is a test document about machine learning.",
            "Another test document about artificial intelligence.",
            "A third document about neural networks."
        ]
        
        # Generate embeddings
        test_chunks = [
            {
                'content': text,
                'section_name': f'Section_{i}',
                'section_type': 'content',
                'chunk_index': i
            }
            for i, text in enumerate(test_texts)
        ]
        
        enriched_chunks = embedding_service.encode_chunks(test_chunks)
        print(f"   Generated {len(enriched_chunks)} embeddings")
        print(f"   Embedding dimension: {enriched_chunks[0]['embedding'].shape}")
        
        # Test 3: Store in Qdrant
        print("3. Testing Qdrant storage...")
        vectors = [chunk['embedding'] for chunk in enriched_chunks]
        payloads = [
            {
                'content': chunk['content'],
                'section_name': chunk['section_name'],
                'test_mode': True
            }
            for chunk in enriched_chunks
        ]
        
        storage_request = StorageRequest(
            vectors=vectors,
            payloads=payloads,
            ids=[str(uuid.uuid4()) for i in range(len(vectors))],  # Use UUIDs instead of string IDs
            collection_name="test_collection"
        )
        
        storage_success = await qdrant_client.store_vectors(storage_request)
        print(f"   Storage result: {'✅ Success' if storage_success else '❌ Failed'}")
        
        if storage_success:
            print("🎉 All tests passed!")
            return True
        else:
            print("❌ Storage test failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_qdrant_connection())
    sys.exit(0 if result else 1)