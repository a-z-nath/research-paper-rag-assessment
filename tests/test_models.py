#!/usr/bin/env python3
"""
Database setup and testing script for SQLAlchemy models
"""
import sys
import os
import uuid
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import engine, create_tables, get_database_session
from src.models import Paper, Chunk, PaperStats, Query

def test_models():
    """Test SQLAlchemy models by creating sample data"""
    print("🔧 Creating database tables...")
    
    try:
        # Create all tables
        create_tables()
        print("✅ Tables created successfully!")
        
        # Get database session
        session = get_database_session()
        
        print("\n📊 Testing models with sample data...")
        
        # Test Paper model
        print("📄 Testing Paper model...")
        paper = Paper(
            title="Test Research Paper",
            authors="John Doe, Jane Smith",
            year=2024,
            file_name="test_paper.pdf",
            file_path="/uploads/test_paper.pdf",
            num_pages=10
        )
        session.add(paper)
        session.commit()
        print(f"✅ Created paper: {paper}")
        
        # Test PaperStats model
        print("📈 Testing PaperStats model...")
        stats = PaperStats(
            paper_id=paper.id,
            views_count=5,
        )
        session.add(stats)
        session.commit()
        print(f"✅ Created paper stats: {stats}")
        
        # Test Chunk model
        print("🧩 Testing Chunk model...")
        chunk = Chunk(
            paper_id=paper.id,
            section="Abstract",
            chunk_index=1,
            snippet="This is a test chunk from the abstract section.",
            qdrant_id=f"chunk_{uuid.uuid4()}"
        )
        session.add(chunk)
        session.commit()
        print(f"✅ Created chunk: {chunk}")
        
        # Test Query model
        print("🔍 Testing Query model...")
        query = Query(
            question="What is the main contribution of this paper?",
            answer="The main contribution is testing the database models.",
            confidence=0.85,
            top_k=5,
            paper_ids=[paper.id],
            sourced_paper_ids=[paper.id],
            citation_chunk_ids=[chunk.id]
        )
        session.add(query)
        session.commit()
        print(f"✅ Created query: {query}")
        
        # Test relationships
        print("\n🔗 Testing relationships...")
        
        # Get paper with its chunks
        paper_with_chunks = session.query(Paper).filter(Paper.id == paper.id).first()
        print(f"📄 Paper '{paper_with_chunks.title}' has {len(paper_with_chunks.chunks)} chunks")
        
        # Get paper with its stats
        paper_with_stats = session.query(Paper).filter(Paper.id == paper.id).first()
        stats_record = session.query(PaperStats).filter(PaperStats.paper_id == paper.id).first()
        if stats_record:
            print(f"📊 Paper has {stats_record.views_count} views and {stats_record.queries_count} queries")
        
        # Test queries
        print("\n🔍 Testing database queries...")
        
        # Count records
        paper_count = session.query(Paper).count()
        chunk_count = session.query(Chunk).count()
        query_count = session.query(Query).count()
        stats_count = session.query(PaperStats).count()
        
        print(f"📊 Database contains:")
        print(f"   📄 Papers: {paper_count}")
        print(f"   🧩 Chunks: {chunk_count}")
        print(f"   🔍 Queries: {query_count}")
        print(f"   📈 Stats: {stats_count}")
        
        # Cleanup test data
        print("\n🧹 Cleaning up test data...")
        session.delete(query)
        session.delete(chunk)
        session.delete(stats)
        session.delete(paper)
        session.commit()
        print("✅ Test data cleaned up")
        
        session.close()
        
        print("\n🎉 All model tests passed! Database schema is ready.")
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

def show_table_info():
    """Show information about created tables"""
    print("\n📋 Database Schema Information:")
    print("=" * 50)
    
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    for table_name in inspector.get_table_names():
        print(f"\n📊 Table: {table_name}")
        columns = inspector.get_columns(table_name)
        for column in columns:
            nullable = "NULL" if column['nullable'] else "NOT NULL"
            print(f"   └─ {column['name']}: {column['type']} {nullable}")
        
        # Show indexes
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print(f"   🔍 Indexes:")
            for index in indexes:
                print(f"      └─ {index['name']}: {index['column_names']}")

if __name__ == "__main__":
    print("🚀 Setting up database schema...")
    print("=" * 50)
    
    if test_models():
        show_table_info()
        print("\n✅ Database setup completed successfully!")
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)