"""
Topic Analytics models for storing TF-IDF based topic analysis
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from .base import BaseModel

class TopicAnalytics(BaseModel):
    """Model for storing computed topics with TF-IDF scores"""
    __tablename__ = "topic_analytics"
    
    topic = Column(String(255), nullable=False, index=True)
    query_count = Column(Integer, default=0, nullable=False)
    tfidf_score = Column(Float, nullable=False)
    sample_questions = Column(ARRAY(Text), default=[], nullable=False)
    last_updated = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    
    # Add check constraints
    __table_args__ = (
        CheckConstraint("query_count >= 0", name="check_positive_query_count"),
        CheckConstraint("tfidf_score >= 0", name="check_positive_tfidf_score"),
    )
    
    def __repr__(self):
        return f"<TopicAnalytics(topic='{self.topic}', count={self.query_count}, score={self.tfidf_score:.4f})>"

class TopicGenerationLog(BaseModel):
    """Model for tracking topic generation processing"""
    __tablename__ = "topic_generation_log"
    
    last_processed_timestamp = Column(DateTime(timezone=True), nullable=False)
    total_queries_processed = Column(Integer, default=0, nullable=False)
    topics_generated = Column(Integer, default=0, nullable=False)
    processing_time = Column(Float, default=0.0, nullable=False)
    
    # Add check constraints
    __table_args__ = (
        CheckConstraint("total_queries_processed >= 0", name="check_positive_queries_processed"),
        CheckConstraint("topics_generated >= 0", name="check_positive_topics_generated"),
        CheckConstraint("processing_time >= 0", name="check_positive_processing_time"),
    )
    
    def __repr__(self):
        return f"<TopicGenerationLog(processed={self.total_queries_processed}, topics={self.topics_generated})>"