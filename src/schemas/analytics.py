"""
Analytics and statistics related Pydantic schemas
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class PopularTopic(BaseModel):
    """Popular query topic"""
    topic: str = Field(..., description="Topic or keyword")
    count: int = Field(..., ge=0, description="Number of queries")
    percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of total queries")

class PopularTopics(BaseModel):
    """Schema for popular topics analytics"""
    topics: List[PopularTopic] = Field(..., description="List of popular topics")
    total_queries: int = Field(..., ge=0, description="Total number of queries analyzed")
    period: str = Field(..., description="Time period for analysis")

class QueryHistory(BaseModel):
    """Query history item for analytics"""
    id: UUID = Field(..., description="Query UUID")
    question: str = Field(..., description="Query question")
    answer: Optional[str] = Field(None, description="Generated answer")
    confidence: Optional[float] = Field(None, description="Answer confidence")
    created_at: datetime = Field(..., description="Query timestamp")
    papers_used: List[str] = Field(..., description="Paper titles used in response")

    class Config:
        from_attributes = True

class PaperStats(BaseModel):
    """Extended paper statistics"""
    paper_id: UUID = Field(..., description="Paper UUID")
    title: str = Field(..., description="Paper title")
    views_count: int = Field(..., ge=0, description="Total views")
    queries_count: int = Field(..., ge=0, description="Total queries")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    avg_confidence: Optional[float] = Field(None, description="Average confidence of queries")

class SystemStats(BaseModel):
    """Overall system statistics"""
    total_papers: int = Field(..., ge=0, description="Total papers in system")
    total_queries: int = Field(..., ge=0, description="Total queries processed")
    total_chunks: int = Field(..., ge=0, description="Total text chunks stored")
    avg_processing_time: float = Field(..., ge=0.0, description="Average query processing time")
    storage_used: str = Field(..., description="Storage space used")
    uptime: str = Field(..., description="System uptime")

class AnalyticsResponse(BaseModel):
    """Analytics dashboard response"""
    system_stats: SystemStats = Field(..., description="System-wide statistics")
    popular_topics: List[PopularTopic] = Field(..., description="Most queried topics")
    top_papers: List[PaperStats] = Field(..., description="Most accessed papers")
    recent_queries: List[QueryHistory] = Field(..., description="Recent query history")