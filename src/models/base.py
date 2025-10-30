"""
Base model configuration for SQLAlchemy
"""
import uuid
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, DateTime

Base = declarative_base()

class BaseModel(Base):
    """Abstract base model with common fields"""
    __abstract__ = True
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )