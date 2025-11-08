"""
Database models for RAG system
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Paper(Base):
    """Research paper metadata"""
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    authors = Column(Text)  # Comma-separated or JSON
    year = Column(Integer)
    filename = Column(String(255), unique=True, nullable=False)
    file_path = Column(String(500))
    total_pages = Column(Integer)
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)  # 0: pending, 1: success, -1: failed
    chunk_count = Column(Integer, default=0)
    
    # Relationships
    queries = relationship("Query", back_populates="paper")
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "filename": self.filename,
            "total_pages": self.total_pages,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "processed": self.processed,
            "chunk_count": self.chunk_count
        }


class Query(Base):
    """Query history and analytics"""
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True)
    paper_ids_filter = Column(JSON)  # For multi-paper queries
    top_k = Column(Integer, default=5)
    response_time = Column(Float)  # in seconds
    confidence = Column(Float)
    sources_used = Column(JSON)  # List of filenames
    citations = Column(JSON)  # Full citation objects
    query_date = Column(DateTime, default=datetime.utcnow)
    user_rating = Column(Integer)  # Optional: 1-5 stars
    
    # Relationships
    paper = relationship("Paper", back_populates="queries")
    
    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "paper_ids": self.paper_ids_filter,
            "response_time": self.response_time,
            "confidence": self.confidence,
            "sources_used": self.sources_used,
            "citations": self.citations,
            "query_date": self.query_date.isoformat() if self.query_date else None,
            "user_rating": self.user_rating
        }
