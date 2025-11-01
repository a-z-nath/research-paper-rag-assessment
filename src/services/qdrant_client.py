"""
Qdrant Client Service for Vector Operations

This service handles:
- Collection management (create, delete, configure)
- Vector storage with metadata
- Similarity search and retrieval
- Batch operations for efficiency
- Error handling and connection management
"""

import logging
import uuid
import asyncio
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
import numpy as np
import time

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance, VectorParams, CollectionStatus,
    PointStruct, Filter, FieldCondition, Match, Range,
    UpdateResult, ScoredPoint
)

from config import Settings

logger = logging.getLogger(__name__)

@dataclass
class VectorSearchResult:
    """Container for vector search results"""
    id: str
    score: float
    payload: Dict[str, Any]
    vector: Optional[np.ndarray] = None

@dataclass
class SearchRequest:
    """Search request configuration"""
    query_vector: np.ndarray
    collection_name: str
    top_k: int = 5
    score_threshold: float = 0.0
    filter_conditions: Optional[Dict[str, Any]] = None
    return_vectors: bool = False

@dataclass
class StorageRequest:
    """Storage request for vectors with metadata"""
    vectors: List[np.ndarray]
    payloads: List[Dict[str, Any]]
    ids: Optional[List[str]] = None
    collection_name: str = "papers"

settings = Settings()
class QdrantClientService:
    """
    Qdrant client service for vector operations in RAG system
    
    Handles vector storage, similarity search, and collection management
    optimized for research paper chunks and metadata.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "papers",
        embedding_dim: int = 384,  # MiniLM-L6-v2 dimension
        distance_metric: Distance = Distance.COSINE,
        timeout: float = 60.0
    ):
        """
        Initialize Qdrant client service
        
        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Default collection name
            embedding_dim: Dimension of embeddings
            distance_metric: Distance metric for similarity search
            timeout: Request timeout in seconds
        """
        self.host = settings.QDRANT_HOST
        self.port = settings.QDRANT_PORT
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.distance_metric = distance_metric
        self.timeout = timeout
        
        # Initialize client (will be created lazily)
        self._client = None
        self._collection_exists = {}  # Cache collection existence
        
        logger.info(f"Initializing QdrantClientService: {host}:{port}")
        logger.info(f"Default collection: {collection_name}, Embedding dim: {embedding_dim}")

    @property
    def client(self) -> QdrantClient:
        """Lazy initialization of Qdrant client"""
        if self._client is None:
            self._client = QdrantClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout
            )
            logger.info("Qdrant client initialized")
        return self._client

    # async def ensure_collection_exists(self, collection_name: Optional[str] = None) -> bool:
    #     """
    #     Ensure collection exists, create if necessary
        
    #     Args:
    #         collection_name: Collection name (uses default if None)
            
    #     Returns:
    #         True if collection exists or was created successfully
    #     """
    #     collection_name = collection_name or self.collection_name
        
    #     # Check cache first
    #     if collection_name in self._collection_exists:
    #         return self._collection_exists[collection_name]
        
    #     try:
    #         # Check if collection exists
    #         collections = self.client.get_collections()
    #         existing_names = [col.name for col in collections.collections]
            
    #         if collection_name in existing_names:
    #             logger.info(f"Collection '{collection_name}' already exists")
    #             self._collection_exists[collection_name] = True
    #             return True
            
    #         # Create collection
    #         logger.info(f"Creating collection '{collection_name}'...")
            
    #         await self.client.create_collection(
    #             collection_name=collection_name,
    #             vectors_config=VectorParams(
    #                 size=self.embedding_dim,
    #                 distance=self.distance_metric
    #             ),
    #             # Optional: Configure HNSW parameters for better performance
    #             hnsw_config=models.HnswConfigDiff(
    #                 m=16,  # Number of bi-directional links for each node
    #                 ef_construct=200,  # Size of the dynamic candidate list
    #                 full_scan_threshold=10000  # Threshold for switching to full scan
    #             )
    #         )
            
    #         logger.info(f"Collection '{collection_name}' created successfully")
    #         self._collection_exists[collection_name] = True
    #         return True
            
    #     except Exception as e:
    #         logger.error(f"Failed to ensure collection exists: {str(e)}")
    #         self._collection_exists[collection_name] = False
    #         return False

    async def ensure_collection_exists(self, collection_name: Optional[str] = None) -> bool:
        collection_name = collection_name or self.collection_name
        logger.debug(f"Ensuring collection '{collection_name}' exists")
        
        if collection_name in self._collection_exists:
            return self._collection_exists[collection_name]

        try:
            collections = self.client.get_collections()  # Remove await
            existing_names = [col.name for col in collections.collections]
            logger.debug(f"Existing collections: {existing_names}")
            
            if collection_name in existing_names:
                logger.info(f"✅ Collection '{collection_name}' already exists")
                self._collection_exists[collection_name] = True
                return True

            logger.info(f"🚀 Creating collection '{collection_name}'...")

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=self.distance_metric
                )
            )

            logger.info(f"✅ Collection '{collection_name}' created successfully")
            self._collection_exists[collection_name] = True
            return True

        except Exception as e:
            logger.error(f"❌ Failed to ensure collection exists: {e}")
            self._collection_exists[collection_name] = False
            return False


    async def store_vectors(self, storage_request: StorageRequest) -> bool:
        """
        Store vectors with metadata in Qdrant
        
        Args:
            storage_request: Storage request with vectors and metadata
            
        Returns:
            True if storage was successful
        """
        collection_name = storage_request.collection_name
        vectors = storage_request.vectors
        payloads = storage_request.payloads
        ids = storage_request.ids
        
        if len(vectors) != len(payloads):
            raise ValueError("Number of vectors must match number of payloads")
        
        collection = await self.ensure_collection_exists(collection_name)
        # Ensure collection exists
        if not collection:
            raise RuntimeError(f"Could not ensure collection '{collection_name}' exists")
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
        
        logger.info(f"Storing {len(vectors)} vectors in collection '{collection_name}'")
        start_time = time.time()
        
        try:
            # Prepare points for batch upload
            points = []
            for i, (vector, payload, point_id) in enumerate(zip(vectors, payloads, ids)):
                # Ensure vector is the right type and shape
                if isinstance(vector, np.ndarray):
                    vector = vector.tolist()
                
                # Validate vector dimension
                if len(vector) != self.embedding_dim:
                    raise ValueError(f"Vector dimension {len(vector)} doesn't match expected {self.embedding_dim}")
                
                # Add internal metadata
                enriched_payload = payload.copy()
                enriched_payload.update({
                    "stored_at": time.time(),
                    "vector_id": point_id,
                    "batch_index": i
                })
                
                point = PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=enriched_payload
                )
                points.append(point)
            
            # Batch upload to Qdrant
            operation_info = self.client.upsert(
                collection_name=collection_name,
                wait=True,  # Wait for the operation to complete
                points=points
            )
            
            storage_time = time.time() - start_time
            logger.info(f"Successfully stored {len(vectors)} vectors in {storage_time:.2f}s")
            logger.info(f"Operation status: {operation_info.status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store vectors: {str(e)}")
            return False

    async def search_similar(self, search_request: SearchRequest) -> List[VectorSearchResult]:
        """
        Search for similar vectors
        
        Args:
            search_request: Search configuration and query vector
            
        Returns:
            List of search results with scores and metadata
        """
        collection_name = search_request.collection_name
        query_vector = search_request.query_vector
        top_k = search_request.top_k
        score_threshold = search_request.score_threshold
        filter_conditions = search_request.filter_conditions
        return_vectors = search_request.return_vectors
        
        # Ensure collection exists
        if not await self.ensure_collection_exists(collection_name):
            logger.warning(f"Collection '{collection_name}' doesn't exist")
            return []
        
        logger.info(f"Searching for {top_k} similar vectors in '{collection_name}'")
        start_time = time.time()
        
        try:
            # Prepare query vector
            if isinstance(query_vector, np.ndarray):
                query_vector = query_vector.tolist()
            
            # Build filter if provided
            query_filter = None
            if filter_conditions:
                query_filter = self._build_filter(filter_conditions)
            
            # Perform search
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=return_vectors
            )
            
            search_time = time.time() - start_time
            logger.info(f"Found {len(search_results)} results in {search_time:.3f}s")
            
            # Convert to our result format
            results = []
            for result in search_results:
                vector_result = VectorSearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload or {},
                    vector=np.array(result.vector) if result.vector else None
                )
                results.append(vector_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []

    def _build_filter(self, filter_conditions: Dict[str, Any]) -> Filter:
        """
        Build Qdrant filter from conditions
        
        Args:
            filter_conditions: Dictionary of filter conditions
            
        Returns:
            Qdrant Filter object
        """
        must_conditions = []
        
        for field, condition in filter_conditions.items():
            if isinstance(condition, dict):
                if "match" in condition:
                    # Exact match
                    must_conditions.append(
                        FieldCondition(
                            key=field,
                            match=Match(value=condition["match"])
                        )
                    )
                elif "any" in condition:
                    # Match any of the values
                    from qdrant_client.http.models import MatchAny
                    must_conditions.append(
                        FieldCondition(
                            key=field,
                            match=MatchAny(any=condition["any"])
                        )
                    )
                elif "range" in condition:
                    # Range condition
                    range_cond = condition["range"]
                    must_conditions.append(
                        FieldCondition(
                            key=field,
                            range=Range(
                                gte=range_cond.get("gte"),
                                lte=range_cond.get("lte"),
                                gt=range_cond.get("gt"),
                                lt=range_cond.get("lt")
                            )
                        )
                    )
            else:
                # Simple value match
                must_conditions.append(
                    FieldCondition(
                        key=field,
                        match=Match(value=condition)
                    )
                )
        
        return Filter(must=must_conditions)

    async def delete_vectors(self, collection_name: str, vector_ids: List[str]) -> bool:
        """
        Delete vectors by IDs
        
        Args:
            collection_name: Collection name
            vector_ids: List of vector IDs to delete
            
        Returns:
            True if deletion was successful
        """
        if not vector_ids:
            return True
        
        logger.info(f"Deleting {len(vector_ids)} vectors from '{collection_name}'")
        
        try:
            operation_info = self.client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(
                    points=vector_ids
                ),
                wait=True
            )
            
            logger.info(f"Deletion operation status: {operation_info.status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vectors: {str(e)}")
            return False

    async def get_collection_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get collection information and statistics
        
        Args:
            collection_name: Collection name (uses default if None)
            
        Returns:
            Dictionary with collection information
        """
        collection_name = collection_name or self.collection_name
        
        try:
            collection_info = self.client.get_collection(collection_name)
            
            return {
                "name": collection_name,
                "status": collection_info.status,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "config": {
                    "params": collection_info.config.params.dict() if collection_info.config.params else {},
                    "hnsw_config": collection_info.config.hnsw_config.dict() if collection_info.config.hnsw_config else {},
                    "optimizer_config": collection_info.config.optimizer_config.dict() if collection_info.config.optimizer_config else {}
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info: {str(e)}")
            return {}

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Qdrant server
        
        Returns:
            Test results with connection status and performance
        """
        logger.info("Testing Qdrant connection...")
        
        try:
            start_time = time.time()
            
            # Test basic connection
            collections = self.client.get_collections()
            connection_time = time.time() - start_time
            
            # Test collection creation (with cleanup)
            test_collection = f"test_collection_{int(time.time())}"
            
            creation_start = time.time()
            await self.ensure_collection_exists(test_collection)
            creation_time = time.time() - creation_start
            
            # Test vector operations
            test_vector = np.random.random(self.embedding_dim).tolist()
            test_payload = {"test": True, "timestamp": time.time()}
            
            storage_start = time.time()
            storage_request = StorageRequest(
                vectors=[test_vector],
                payloads=[test_payload],
                collection_name=test_collection
            )
            await self.store_vectors(storage_request)
            storage_time = time.time() - storage_start
            
            # Test search
            search_start = time.time()
            search_request = SearchRequest(
                query_vector=np.array(test_vector),
                collection_name=test_collection,
                top_k=1
            )
            results = await self.search_similar(search_request)
            search_time = time.time() - search_start
            
            # Cleanup test collection
            try:
                self.client.delete_collection(test_collection)
            except:
                pass
            
            total_time = time.time() - start_time
            
            return {
                "success": True,
                "connection_time": connection_time,
                "creation_time": creation_time,
                "storage_time": storage_time,
                "search_time": search_time,
                "total_time": total_time,
                "collections_count": len(collections.collections),
                "test_results_found": len(results),
                "qdrant_version": "latest"  # Could be extracted from server info
            }
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_time": time.time() - start_time if 'start_time' in locals() else 0
            }

    async def cleanup_collection(self, collection_name: Optional[str] = None) -> bool:
        """
        Delete entire collection (use with caution!)
        
        Args:
            collection_name: Collection to delete (uses default if None)
            
        Returns:
            True if deletion was successful
        """
        collection_name = collection_name or self.collection_name
        
        logger.warning(f"Deleting entire collection: {collection_name}")
        
        try:
            self.client.delete_collection(collection_name)
            
            # Remove from cache
            if collection_name in self._collection_exists:
                del self._collection_exists[collection_name]
            
            logger.info(f"Collection '{collection_name}' deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete collection: {str(e)}")
            return False

    def __del__(self):
        """Cleanup when service is destroyed"""
        if hasattr(self, '_client') and self._client:
            try:
                # Close client connection if needed
                pass
            except:
                pass