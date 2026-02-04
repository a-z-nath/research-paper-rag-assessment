"""
Chunk model for storing text chunks and their Qdrant references
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import BaseModel

class Chunk(BaseModel):
    """Text chunk model for embeddings and Qdrant vector references"""
    __tablename__ = "chunks"
    
    paper_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("papers.id", ondelete="CASCADE"), 
        nullable=False
    )
    section = Column(Text, nullable=False)  # e.g., "Abstract", "Introduction"
    chunk_index = Column(Integer, nullable=False)  # order within section
    snippet = Column(Text, nullable=False)  # the chunk text
    qdrant_id = Column(Text, unique=True, nullable=False)  # corresponding vector ID in Qdrant
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    
    # Relationship to Paper
    paper = relationship("Paper", backref="chunks")
    
    # Index for faster queries
    __table_args__ = (
        Index("idx_chunks_paper_id", "paper_id"),
    )
    
    def __repr__(self):
        return f"<Chunk(id={self.id}, paper_id={self.paper_id}, section='{self.section}', qdrant_id='{self.qdrant_id}')>"