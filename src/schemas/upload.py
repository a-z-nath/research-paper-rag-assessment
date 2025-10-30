"""
File upload related Pydantic schemas
"""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator
from fastapi import UploadFile

class FileUpload(BaseModel):
    """Schema for file upload validation"""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME content type")
    size: int = Field(..., ge=1, description="File size in bytes")

    @validator('filename')
    def validate_filename(cls, v):
        if not v.strip():
            raise ValueError('Filename cannot be empty')
        if not v.lower().endswith('.pdf'):
            raise ValueError('Only PDF files are allowed')
        return v.strip()

    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['application/pdf']
        if v not in allowed_types:
            raise ValueError(f'Content type must be one of: {allowed_types}')
        return v

    @validator('size')
    def validate_file_size(cls, v):
        max_size = 50 * 1024 * 1024  # 50MB
        if v > max_size:
            raise ValueError(f'File size cannot exceed {max_size // (1024 * 1024)}MB')
        return v

class UploadResponse(BaseModel):
    """Schema for file upload responses"""
    paper_id: UUID = Field(..., description="Generated paper UUID")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Storage path")
    size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")

class ProcessingStatus(BaseModel):
    """Schema for processing status updates"""
    paper_id: UUID = Field(..., description="Paper UUID")
    status: str = Field(..., description="Current processing status")
    progress: float = Field(..., ge=0.0, le=100.0, description="Processing progress percentage")

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FileUploadResult(BaseModel):
    """Result for individual file upload"""
    file_name: str
    success: bool
    message: str
    paper_id: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    num_pages: Optional[int] = None
    chunks_created: Optional[int] = None
    file_path: Optional[str] = None
    processing_time: Optional[float] = None
    error_details: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """Response model for batch paper upload"""
    success: bool
    message: str
    collection_name: str
    total_files: int
    successful_uploads: int
    failed_uploads: int
    uploaded_papers: List[FileUploadResult]
    total_processing_time: float


class PaperUploadResponse(BaseModel):
    """Response model for single paper upload (legacy)"""
    success: bool
    message: str
    paper_id: Optional[str] = None
    title: Optional[str] = None
    file_name: Optional[str] = None
    processing_time: Optional[float] = None

class UploadStatus:
    """Upload processing status constants"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    message: str = Field(..., description="Current processing step")
    error: Optional[str] = Field(None, description="Error message if any")