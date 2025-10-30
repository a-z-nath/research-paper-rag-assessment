#!/usr/bin/env python3
"""
Infrastructure testing script to verify Qdrant, Ollama, and PostgreSQL connections
"""
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

async def test_qdrant():
    """Test Qdrant vector database connection and basic operations"""
    print("🔍 Testing Qdrant connection...")
    
    try:
        # Initialize client
        client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333))
        )
        
        # Test basic connection
        collections = client.get_collections()
        print(f"✅ Qdrant connected successfully!")
        print(f"📊 Current collections: {len(collections.collections)}")
        
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
        print(f"✅ Created test collection: {test_collection_name}")
        
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
        print("✅ Successfully inserted test vector")
        
        # Test searching
        search_results = client.search(
            collection_name=test_collection_name,
            query_vector=test_vector,
            limit=1
        )
        print(f"✅ Search test successful! Found {len(search_results)} results")
        
        # Cleanup
        client.delete_collection(test_collection_name)
        print("✅ Cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Qdrant test failed: {e}")
        return False

def test_postgresql():
    """Test PostgreSQL database connection"""
    print("\n🐘 Testing PostgreSQL connection...")
    
    try:
        # Get database URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ PostgreSQL connected successfully!")
        print(f"📊 Database version: {version[0]}")
        
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
        print(f"✅ Test insert successful! ID: {test_id}")
        
        # Test select
        cursor.execute("SELECT COUNT(*) FROM test_table;")
        count = cursor.fetchone()[0]
        print(f"✅ Test select successful! Records: {count}")
        
        # Cleanup
        cursor.execute("DROP TABLE IF EXISTS test_table;")
        conn.commit()
        
        cursor.close()
        conn.close()
        print("✅ Cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL test failed: {e}")
        return False

async def test_ollama():
    """Test Ollama LLM service connection"""
    print("\n🤖 Testing Ollama connection...")
    
    try:
        # Check if using cloud or local Ollama
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        api_key = os.getenv("OLLAMA_API_KEY")
        model = os.getenv("OLLAMA_MODEL", "llama3")
        
        print(f"📡 Testing connection to: {base_url}")
        print(f"🎯 Using model: {model}")
        
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
                print(f"✅ Ollama service is running!")
                
                # Test generation
                response = await client.post(
                    f"{base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": "Hello, respond with just 'Hi there!'",
                        "stream": False
                    }
                )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "No response")
                print(f"✅ Ollama generation test successful!")
                print(f"🎯 Generated text: {generated_text[:100]}...")
                return True
            else:
                print(f"❌ Ollama generation failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")
        print("💡 Make sure Ollama is running and the model is pulled")
        if "localhost" in base_url:
            print("💡 For local setup, run: ollama serve && ollama pull llama3")
        return False

async def main():
    """Run all infrastructure tests"""
    print("🚀 Starting Infrastructure Tests")
    print("=" * 50)
    
    # Test all services
    qdrant_ok = await test_qdrant()
    postgres_ok = test_postgresql()
    ollama_ok = await test_ollama()
    
    print("\n" + "=" * 50)
    print("📊 Infrastructure Test Results:")
    print(f"🔍 Qdrant: {'✅ PASS' if qdrant_ok else '❌ FAIL'}")
    print(f"🐘 PostgreSQL: {'✅ PASS' if postgres_ok else '❌ FAIL'}")
    print(f"🤖 Ollama: {'✅ PASS' if ollama_ok else '❌ FAIL'}")
    
    if all([qdrant_ok, postgres_ok, ollama_ok]):
        print("\n🎉 All infrastructure tests passed! Ready to proceed with development.")
        return True
    else:
        print("\n⚠️ Some tests failed. Please fix the issues before proceeding.")
        return False

if __name__ == "__main__":
    asyncio.run(main())