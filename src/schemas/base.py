"""
Base Pydantic schemas for common API responses
"""
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = Field(..., description="Whether the request was successful")
    message: Optional[str] = Field(None, description="Human-readable message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

class SuccessResponse(BaseResponse):
    """Success response model"""
    success: bool = Field(True, description="Success indicator")
    data: Optional[Any] = Field(None, description="Response data")

class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = Field(False, description="Error indicator")
    error_code: Optional[str] = Field(None, description="Error code for debugging")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

class HealthResponse(BaseModel):
    """Health check response"""
    success: bool = Field(True, description="Health status")

class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

class PaginatedResponse(BaseModel):
    """Paginated response model"""
    data: list = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")