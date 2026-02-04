"""
Paper model for storing research paper metadata
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import BaseModel

class Paper(BaseModel):
    """Research paper metadata model"""
    __tablename__ = "papers"
    
    title = Column(Text, nullable=False)
    authors = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    file_name = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)  # e.g., /upload/<file>.pdf
    full_text = Column(Text, nullable=True)  # Complete extracted text from PDF
    num_pages = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    status = Column(
        Text, 
        default="active", 
        server_default="active",
        nullable=False
    )
    
    # Add check constraint for status
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'deleted')",
            name="check_paper_status"
        ),
    )
    
    def __repr__(self):
        return f"<Paper(id={self.id}, title='{self.title[:50]}...', status='{self.status}')>"