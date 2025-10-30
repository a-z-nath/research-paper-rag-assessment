"""
Query-related Pydantic schemas
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, validator

class Citation(BaseModel):
    """Citation information for query responses"""
    paper_id: str = Field(..., description="Paper UUID")
    chunk_id: str = Field(..., description="Chunk/Qdrant vector ID")
    paper_title: str = Field(..., description="Title of the source paper")
    section: str = Field(..., description="Section name (e.g., Introduction, Methods)")
    snippet: str = Field(..., description="Relevant text snippet from the paper")
    page: Optional[int] = Field(default=None, description="Page number in the original paper")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score from vector search")

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
    paper_ids: Optional[List[str]] = Field(
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
    question: str = Field(..., description="Original question asked")
    answer: str = Field(..., description="Generated answer from LLM")
    citations: List[Citation] = Field(default=[], description="List of citations supporting the answer")
    sourced_paper_used: List[str] = Field(default=[], description="List of paper IDs used to generate the answer")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the answer")
    query_id: str = Field(..., description="Unique query identifier")
    response_time: float = Field(..., description="Time taken to process the query in seconds")

class QueryHistoryItem(BaseModel):
    """Individual query history item"""
    query_id: str
    question: str
    answer: str
    confidence: float
    response_time: float
    created_at: datetime
    sourced_papers_count: int
    citations_count: int

class QueryHistoryResponse(BaseModel):
    """Response schema for query history listing"""
    success: bool
    queries: List[QueryHistoryItem]
    total: int
    page: int
    limit: int
    total_pages: int

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