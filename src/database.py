"""
Database connection and session management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Import Base first
from .models.base import Base

load_dotenv()

# Import models after Base to avoid circular imports
from .models.paper import Paper
from .models.chunk import Chunk  
from .models.paper_stats import PaperStats
from .models.query import Query
from .models.topic_analytics import TopicAnalytics, TopicGenerationLog

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create engine
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Disable connection pooling for simplicity
    echo=os.getenv("DEBUG", "false").lower() == "true"  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_database_session() -> Session:
    """Get a database session"""
    return SessionLocal()

def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)
    
def drop_tables():
    """Drop all tables in the database (use with caution!)"""
    Base.metadata.drop_all(bind=engine)

async def init_database():
    """Initialize database with tables"""
    try:
        create_tables()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise