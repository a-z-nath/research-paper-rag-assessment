"""
Embedding service using sentence-transformers (lazy-loaded to speed up API startup)
"""
from typing import List, Optional
import numpy as np


class EmbeddingService:
    """Generate embeddings for text using sentence-transformers"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding service (model is loaded on first use)
        """
        self.model_name = model_name
        self.model: Optional[object] = None
        self.dimension: Optional[int] = None

    def _ensure_model(self):
        """Lazily load the embedding model when first needed"""
        if self.model is None:
            print(f"Loading embedding model: {self.model_name}")
            # Import here to avoid heavy import at server startup
            from sentence_transformers import SentenceTransformer  # type: ignore
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            print(f"✅ Embedding model loaded. Dimension: {self.dimension}")
    
    def embed_text(self, text: str, normalize: bool = True) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            normalize: Whether to normalize the embedding (recommended for cosine similarity)
            
        Returns:
            List of floats representing the embedding
        """
        try:
            self._ensure_model()
            # Clean text before embedding for better quality
            text = self._preprocess_text(text)
            embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=normalize)
            return embedding.tolist()
        except Exception as e:
            print(f"Error embedding text: {str(e)}")
            dim = self.dimension or 384
            return [0.0] * dim
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for better embedding quality
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = ' '.join(text.split())
        # Truncate if too long (most models have max length ~512 tokens)
        max_chars = 2000  # ~500 tokens
        if len(text) > max_chars:
            text = text[:max_chars]
        return text
    
    def embed_texts(self, texts: List[str], batch_size: int = 32, normalize: bool = True) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            normalize: Whether to normalize embeddings (recommended)
            
        Returns:
            List of embeddings
        """
        try:
            self._ensure_model()
            # Preprocess all texts
            texts = [self._preprocess_text(t) for t in texts]
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True,
                normalize_embeddings=normalize
            )
            return embeddings.tolist()
        except Exception as e:
            print(f"Error embedding texts: {str(e)}")
            dim = self.dimension or 384
            return [[0.0] * dim] * len(texts)
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.dimension or 384
