"""
Paper stats model for tracking views and queries
"""
from sqlalchemy import Column, BigInteger, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base

class PaperStats(Base):
    """Paper statistics model for tracking views and queries"""
    __tablename__ = "paper_stats"
    
    paper_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("papers.id", ondelete="CASCADE"), 
        primary_key=True
    )
    views_count = Column(BigInteger, default=0, server_default="0")
    queries_count = Column(BigInteger, default=0, server_default="0")
    
    # Relationship to Paper
    paper = relationship("Paper", backref="stats")
    
    # Index for fast view/query updates
    __table_args__ = (
        Index("idx_paper_stats_counts", "views_count", "queries_count"),
    )
    
    def __repr__(self):
        return f"<PaperStats(paper_id={self.paper_id}, views={self.views_count}, queries={self.queries_count})>"