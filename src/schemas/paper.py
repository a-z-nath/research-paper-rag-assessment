"""
Paper-related Pydantic schemas
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, validator

class PaperBase(BaseModel):
    """Base paper model with common fields"""
    title: str = Field(..., min_length=1, max_length=500, description="Paper title")
    abstract: Optional[str] = Field(None, max_length=5000, description="Paper abstract")
    authors: Optional[str] = Field(None, max_length=1000, description="Comma-separated author names")
    year: Optional[int] = Field(None, ge=1900, le=2030, description="Publication year")

class PaperCreate(PaperBase):
    """Schema for creating a new paper"""
    file_name: str = Field(..., min_length=1, description="Original filename")
    file_path: str = Field(..., min_length=1, description="Storage path")
    num_pages: Optional[int] = Field(None, ge=1, description="Number of pages")

class PaperUpdate(BaseModel):
    """Schema for updating paper metadata"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    abstract: Optional[str] = Field(None, max_length=5000)
    authors: Optional[str] = Field(None, max_length=1000)
    year: Optional[int] = Field(None, ge=1900, le=2030)

class PaperResponse(PaperBase):
    """Schema for paper API responses"""
    id: UUID = Field(..., description="Paper UUID")
    file_name: str = Field(..., description="Original filename")
    num_pages: Optional[int] = Field(None, description="Number of pages")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    status: str = Field(..., description="Paper status")

    class Config:
        from_attributes = True

class PaperSummary(BaseModel):
    """Minimal paper info for lists"""
    id: UUID = Field(..., description="Paper UUID")
    title: str = Field(..., description="Paper title")
    authors: Optional[str] = Field(None, description="Author names")
    year: Optional[int] = Field(None, description="Publication year")
    uploaded_at: datetime = Field(..., description="Upload timestamp")

    class Config:
        from_attributes = True

class PaperListResponse(BaseModel):
    """Response schema for paper listing endpoints"""
    success: bool = Field(..., description="Whether request was successful")
    papers: List[PaperResponse] = Field(..., description="List of papers")
    total: int = Field(..., description="Total number of papers")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Papers per page")
    total_pages: int = Field(..., description="Total number of pages")

class PaperUploadResponse(BaseModel):
    """Response schema for paper upload endpoints"""
    success: bool = Field(..., description="Whether upload was successful")
    paper_id: Optional[UUID] = Field(None, description="Paper UUID if successful")
    message: str = Field(..., description="Upload status message")
    file_name: Optional[str] = Field(None, description="Original filename")
    processing_status: str = Field(..., description="Processing status")

class PaperList(BaseModel):
    """Schema for paper list responses"""
    papers: List[PaperSummary] = Field(..., description="List of papers")
    total: int = Field(..., ge=0, description="Total number of papers")

class PaperStats(BaseModel):
    """Paper statistics schema"""
    paper_id: UUID = Field(..., description="Paper UUID")
    views_count: int = Field(..., ge=0, description="Number of views")
    queries_count: int = Field(..., ge=0, description="Number of queries")

    class Config:
        from_attributes = True