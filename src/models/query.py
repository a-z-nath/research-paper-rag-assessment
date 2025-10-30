"""
Query model for storing search history and analytics
"""
from datetime import datetime
from sqlalchemy import Column, Text, Integer, DateTime, Index, CheckConstraint, ARRAY, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import BaseModel

class Query(BaseModel):
    """Query history model for storing search queries and results"""
    __tablename__ = "queries"
    
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    confidence = Column(
        Numeric(5, 4), 
        nullable=True
    )
    top_k = Column(Integer, default=5, server_default="5")
    paper_ids = Column(
        ARRAY(UUID(as_uuid=True)), 
        default=[], 
        server_default="{}"
    )  # filter used during search
    sourced_paper_ids = Column(
        ARRAY(UUID(as_uuid=True)), 
        default=[], 
        server_default="{}"
    )  # papers that contributed to answer
    citation_chunk_ids = Column(
        ARRAY(UUID(as_uuid=True)), 
        default=[], 
        server_default="{}"
    )  # chunk IDs used in citations
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    
    # Check constraint for confidence
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="check_query_confidence"
        ),
        Index("idx_queries_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<Query(id={self.id}, question='{self.question[:50]}...', confidence={self.confidence})>"