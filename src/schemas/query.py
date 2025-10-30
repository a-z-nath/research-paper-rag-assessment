"""
Query-related Pydantic schemas
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, validator

class Citation(BaseModel):
    """Citation information for query responses"""
    paper_title: str = Field(..., description="Title of the cited paper")
    paper_id: UUID = Field(..., description="UUID of the cited paper")
    section: str = Field(..., description="Section name where information was found")
    page: Optional[int] = Field(None, ge=1, description="Page number")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    snippet: str = Field(..., max_length=500, description="Relevant text snippet")

class QueryRequest(BaseModel):
    """Schema for query requests"""
    question: str = Field(
        ..., 
        min_length=5, 
        max_length=1000, 
        description="The question to ask about the papers"
    )
    top_k: int = Field(
        5, 
        ge=1, 
        le=20, 
        description="Number of top results to retrieve"
    )
    paper_ids: Optional[List[UUID]] = Field(
        None, 
        description="Optional list of paper IDs to limit search to"
    )

    @validator('question')
    def question_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty or only whitespace')
        return v.strip()

class QueryResponse(BaseModel):
    """Schema for query responses"""
    answer: str = Field(..., description="Generated answer to the question")
    citations: List[Citation] = Field(..., description="List of citations supporting the answer")
    sources_used: List[str] = Field(..., description="List of paper titles used as sources")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for the answer")
    processing_time: float = Field(..., ge=0.0, description="Processing time in seconds")

class QueryHistory(BaseModel):
    """Schema for query history"""
    id: UUID = Field(..., description="Query UUID")
    question: str = Field(..., description="Original question")
    answer: Optional[str] = Field(None, description="Generated answer")
    confidence: Optional[float] = Field(None, description="Confidence score")
    created_at: datetime = Field(..., description="Query timestamp")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")

    class Config:
        from_attributes = True

class QueryHistoryList(BaseModel):
    """Schema for query history list"""
    queries: List[QueryHistory] = Field(..., description="List of recent queries")
    total: int = Field(..., ge=0, description="Total number of queries")