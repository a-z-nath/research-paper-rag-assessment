"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class PaperUploadResponse(BaseModel):
    """Response after uploading a paper"""
    paper_id: int
    title: str
    filename: str
    total_pages: int
    chunk_count: int
    message: str


class Citation(BaseModel):
    """Citation information"""
    paper_title: str
    section: Optional[str] = None
    page: int
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    chunk_text: Optional[str] = None


class QueryRequest(BaseModel):
    """Request for querying papers"""
    question: str = Field(..., min_length=3)
    top_k: int = Field(default=5, ge=1, le=20)
    paper_ids: Optional[List[int]] = None


class QueryResponse(BaseModel):
    """Response from query endpoint"""
    answer: str
    citations: List[Citation]
    sources_used: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    response_time: float
    cached: bool = False  # Indicates if response came from cache


class PaperDetail(BaseModel):
    """Detailed paper information"""
    id: int
    title: str
    authors: Optional[str] = None
    year: Optional[int] = None
    filename: str
    total_pages: int
    upload_date: datetime
    chunk_count: int
    
    class Config:
        from_attributes = True


class PaperStats(BaseModel):
    """Paper statistics"""
    paper_id: int
    title: str
    total_queries: int
    avg_confidence: float
    most_common_topics: List[str]


class QueryHistory(BaseModel):
    """Query history entry"""
    id: int
    question: str
    answer: str
    confidence: float
    response_time: float
    query_date: datetime
    sources_used: List[str]
    
    class Config:
        from_attributes = True
