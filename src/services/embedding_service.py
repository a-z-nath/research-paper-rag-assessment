"""
Embedding Service using sentence-transformers with SPECTER model

This service handles:
- Loading and managing the SPECTER model (specialized for scientific papers)
- Converting text chunks to vector embeddings
- Batch processing for efficiency
- Caching and optimization
- Error handling and fallback mechanisms
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import time
from pathlib import Path

# Sentence transformers for embeddings
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Container for embedding results"""
    embeddings: np.ndarray
    texts: List[str]
    model_name: str
    embedding_dim: int
    processing_time: float
    batch_size: int

@dataclass
class EmbeddingMetadata:
    """Metadata for embeddings"""
    chunk_id: str
    paper_id: str
    section_name: str
    chunk_index: int
    text_preview: str  # First 100 chars for debugging

class EmbeddingService:
    """
    Embedding service optimized for research papers using MiniLM model
    
    all-MiniLM-L6-v2 (Lightweight and Fast)
    - General purpose sentence transformer
    - Fast inference and smaller download size
    - 384-dimensional embeddings
    - Good balance of speed and quality for RAG systems
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int = 32,
        max_seq_length: int = 512,
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the embedding service
        
        Args:
            model_name: Name of the sentence-transformer model
            batch_size: Batch size for processing multiple texts
            max_seq_length: Maximum sequence length for the model
            device: Device to run the model on ('cuda', 'cpu', or None for auto)
            cache_dir: Directory to cache the model
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.cache_dir = cache_dir
        
        # Model will be loaded lazily
        self._model = None
        self._embedding_dim = None
        
        logger.info(f"Initializing EmbeddingService with model: {model_name}")
        logger.info(f"Device: {self.device}, Batch size: {batch_size}")

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model"""
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        if self._embedding_dim is None:
            # Load model to get dimension
            _ = self.model
        return self._embedding_dim

    def _load_model(self):
        """Load the sentence transformer model"""
        logger.info(f"Loading model: {self.model_name}")
        start_time = time.time()
        
        try:
            # Load model with specified parameters
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=self.cache_dir
            )
            
            # Set max sequence length
            self._model.max_seq_length = self.max_seq_length
            
            # Get embedding dimension
            sample_embedding = self._model.encode("test", convert_to_numpy=True)
            self._embedding_dim = sample_embedding.shape[0]
            
            load_time = time.time() - start_time
            logger.info(f"Model loaded successfully in {load_time:.2f}s")
            logger.info(f"Embedding dimension: {self._embedding_dim}")
            logger.info(f"Max sequence length: {self.max_seq_length}")
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {str(e)}")
            
            # Fallback to a more reliable model
            logger.info("Attempting fallback to all-MiniLM-L6-v2")
            try:
                self._model = SentenceTransformer(
                    'all-MiniLM-L6-v2',
                    device=self.device,
                    cache_folder=self.cache_dir
                )
                self._model.max_seq_length = self.max_seq_length
                sample_embedding = self._model.encode("test", convert_to_numpy=True)
                self._embedding_dim = sample_embedding.shape[0]
                self.model_name = 'all-MiniLM-L6-v2'  # Update model name
                
                logger.info(f"Fallback model loaded: {self.model_name}")
                logger.info(f"Embedding dimension: {self._embedding_dim}")
                
            except Exception as fallback_error:
                logger.error(f"Fallback model also failed: {str(fallback_error)}")
                raise RuntimeError(f"Could not load any embedding model: {str(e)}")

    def encode_texts(self, texts: List[str], show_progress: bool = True) -> EmbeddingResult:
        """
        Encode a list of texts into embeddings
        
        Args:
            texts: List of text strings to encode
            show_progress: Whether to show progress bar
            
        Returns:
            EmbeddingResult with embeddings and metadata
        """
        if not texts:
            raise ValueError("Cannot encode empty list of texts")
        
        logger.info(f"Encoding {len(texts)} texts with model {self.model_name}")
        start_time = time.time()
        
        try:
            # Clean and validate texts
            cleaned_texts = self._clean_texts(texts)
            
            # Encode with the model
            embeddings = self.model.encode(
                cleaned_texts,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True  # L2 normalize for better similarity
            )
            
            processing_time = time.time() - start_time
            
            logger.info(f"Encoded {len(texts)} texts in {processing_time:.2f}s")
            logger.info(f"Embedding shape: {embeddings.shape}")
            
            return EmbeddingResult(
                embeddings=embeddings,
                texts=cleaned_texts,
                model_name=self.model_name,
                embedding_dim=self.embedding_dim,
                processing_time=processing_time,
                batch_size=self.batch_size
            )
            
        except Exception as e:
            logger.error(f"Error encoding texts: {str(e)}")
            raise RuntimeError(f"Failed to encode texts: {str(e)}")

    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode a single text into embedding
        
        Args:
            text: Text string to encode
            
        Returns:
            Numpy array of embedding
        """
        if not text or not text.strip():
            raise ValueError("Cannot encode empty text")
        
        cleaned_text = self._clean_text(text)
        
        embedding = self.model.encode(
            [cleaned_text],
            convert_to_numpy=True,
            normalize_embeddings=True
        )[0]
        
        return embedding

    def encode_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Encode text chunks with their metadata
        
        Args:
            chunks: List of chunk dictionaries from TextChunker
            
        Returns:
            List of chunks with added 'embedding' field
        """
        if not chunks:
            return []
        
        logger.info(f"Encoding {len(chunks)} chunks")
        
        # Extract texts from chunks
        texts = [chunk['content'] for chunk in chunks]
        
        # Encode all texts
        embedding_result = self.encode_texts(texts, show_progress=True)
        
        # Add embeddings to chunks
        enriched_chunks = []
        for i, chunk in enumerate(chunks):
            enriched_chunk = chunk.copy()
            enriched_chunk['embedding'] = embedding_result.embeddings[i]
            enriched_chunk['embedding_model'] = self.model_name
            enriched_chunk['embedding_dim'] = self.embedding_dim
            enriched_chunks.append(enriched_chunk)
        
        logger.info(f"Successfully added embeddings to {len(enriched_chunks)} chunks")
        return enriched_chunks

    def _clean_texts(self, texts: List[str]) -> List[str]:
        """Clean and validate list of texts"""
        cleaned = []
        for text in texts:
            cleaned_text = self._clean_text(text)
            cleaned.append(cleaned_text)
        return cleaned

    def _clean_text(self, text: str) -> str:
        """Clean and validate single text"""
        if not isinstance(text, str):
            text = str(text)
        
        # Basic cleaning
        text = text.strip()
        
        # Replace multiple whitespace with single space
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Ensure minimum length
        if len(text) < 10:
            text = text + " " * (10 - len(text))  # Pad short texts
        
        # Truncate if too long (model has max sequence length)
        # Leave some buffer for tokenization overhead
        max_chars = self.max_seq_length * 4  # Rough estimate
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
            logger.debug(f"Truncated text to {max_chars} characters")
        
        return text

    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Ensure embeddings are normalized
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        # Ensure result is in [0, 1] range
        return max(0.0, min(1.0, (similarity + 1) / 2))

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            'model_name': self.model_name,
            'embedding_dim': self.embedding_dim,
            'max_seq_length': self.max_seq_length,
            'device': self.device,
            'batch_size': self.batch_size,
            'model_loaded': self._model is not None
        }

    def test_embedding(self, test_text: str = "This is a test scientific paper about machine learning.") -> Dict[str, Any]:
        """
        Test the embedding service with sample text
        
        Args:
            test_text: Text to test with
            
        Returns:
            Test results
        """
        logger.info("Testing embedding service")
        
        try:
            start_time = time.time()
            embedding = self.encode_single(test_text)
            encoding_time = time.time() - start_time
            
            test_results = {
                'success': True,
                'model_name': self.model_name,
                'test_text': test_text,
                'embedding_shape': embedding.shape,
                'embedding_dim': self.embedding_dim,
                'encoding_time': encoding_time,
                'embedding_norm': np.linalg.norm(embedding),
                'sample_values': embedding[:5].tolist()  # First 5 values
            }
            
            logger.info(f"Embedding test successful: {embedding.shape} in {encoding_time:.3f}s")
            return test_results
            
        except Exception as e:
            logger.error(f"Embedding test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'model_name': self.model_name
            }

    def __del__(self):
        """Cleanup when service is destroyed"""
        if hasattr(self, '_model') and self._model is not None:
            # Clear model from memory
            del self._model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()