"""
Pydantic schemas for API request/response validation
"""

from .base import BaseResponse, ErrorResponse, SuccessResponse
from .paper import PaperCreate, PaperResponse, PaperUpdate, PaperList
from .query import QueryRequest, QueryResponse, Citation
from .upload import FileUpload, UploadResponse
from .analytics import QueryHistory, PopularTopics, PaperStats

__all__ = [
    "BaseResponse", "ErrorResponse", "SuccessResponse",
    "PaperCreate", "PaperResponse", "PaperUpdate", "PaperList",
    "QueryRequest", "QueryResponse", "Citation",
    "FileUpload", "UploadResponse",
    "QueryHistory", "PopularTopics", "PaperStats"
]