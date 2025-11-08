"""
Qdrant vector database client

Qdrant is a vector similarity search engine that stores embeddings
and enables fast nearest-neighbor search using cosine similarity.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Optional
from uuid import uuid4


class QdrantService:
    """
    Handle Qdrant vector database operations
    
    This service manages all interactions with Qdrant including:
    - Collection initialization
    - Vector storage (embeddings + metadata)
    - Semantic search (finding similar vectors)
    - Deletion of vectors by paper ID
    """
    
    def __init__(self, host: str, port: int, collection_name: str, vector_dim: int = 384):
        """
        Initialize Qdrant client and ensure collection exists
        
        Args:
            host: Qdrant host (e.g., 'localhost')
            port: Qdrant port (default: 6333)
            collection_name: Name of the collection to use
            vector_dim: Dimension of embedding vectors (must match embedding model)
        """
        print(f"🔌 [Qdrant] Connecting to Qdrant at {host}:{port}")
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.vector_dim = vector_dim
        self._init_collection()
    
    def _init_collection(self):
        """
        Initialize collection if it doesn't exist
        
        Creates a new Qdrant collection with:
        - Cosine distance metric (best for normalized embeddings)
        - Vector dimension matching the embedding model
        """
        try:
            print(f"📦 [Qdrant] Checking collection: {self.collection_name}")
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                print(f"   Creating new collection with {self.vector_dim} dimensions...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_dim,
                        distance=Distance.COSINE  # Cosine similarity for semantic search
                    )
                )
                print(f"✅ Created Qdrant collection: {self.collection_name}")
            else:
                print(f"✅ Qdrant collection exists: {self.collection_name}")
                
        except Exception as e:
            print(f"❌ [Qdrant] Error initializing collection: {str(e)}")
            raise
    
    def add_vectors(
        self,
        vectors: List[List[float]],
        payloads: List[Dict],
        paper_id: int
    ) -> int:
        """
        Add vectors (embeddings) to collection with metadata
        
        Each vector represents one chunk of text from a paper.
        The payload contains metadata like page number, section, and text content.
        
        Args:
            vectors: List of embedding vectors (each is a list of floats)
            payloads: List of metadata dicts (one per vector)
            paper_id: ID of the paper these vectors belong to
            
        Returns:
            Number of vectors successfully added
        """
        try:
            print(f"💾 [Qdrant] Storing {len(vectors)} vectors for paper_id={paper_id}")
            points = []
            for i, (vector, payload) in enumerate(zip(vectors, payloads)):
                # Add paper_id to payload for filtering during search
                payload['paper_id'] = paper_id
                
                # Create point with unique ID, vector, and metadata
                point = PointStruct(
                    id=str(uuid4()),  # Generate unique ID for this chunk
                    vector=vector,
                    payload=payload
                )
                points.append(point)
            
            # Upsert (insert or update) all points at once
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            print(f"✅ [Qdrant] Added {len(points)} vectors for paper_id={paper_id}")
            return len(points)
            
        except Exception as e:
            print(f"❌ [Qdrant] Error adding vectors: {str(e)}")
            return 0
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        paper_ids: Optional[List[int]] = None,
        score_threshold: float = 0.0
    ) -> List[Dict]:
        """
        Search for similar vectors using cosine similarity
        
        This is the core of semantic search - finds chunks most similar
        to the query embedding based on vector distance.
        
        Args:
            query_vector: Query embedding (from user's question)
            top_k: Number of results to return (default: 5)
            paper_ids: Optional filter - only search within specific papers
            score_threshold: Minimum similarity score (0.0-1.0, default: 0.0)
            
        Returns:
            List of search results sorted by relevance, each containing:
            - id: Unique ID of the chunk
            - score: Similarity score (higher = more relevant)
            - payload: Metadata (text, page, section, paper title, etc.)
        """
        try:
            print(f"🔍 [Qdrant] Searching for top {top_k} similar vectors...")
            
            # Build filter if paper_ids provided (narrow search to specific papers)
            query_filter = None
            if paper_ids:
                print(f"   Filtering by paper_ids: {paper_ids}")
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="paper_id",
                            match=MatchValue(value=paper_ids[0] if len(paper_ids) == 1 else paper_ids)
                        )
                    ]
                )
            
            # Perform vector search using cosine similarity
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
                score_threshold=score_threshold
            )
            
            print(f"✅ [Qdrant] Found {len(results)} results")
            if results:
                print(f"   Top score: {results[0].score:.3f}")
            
            # Format results for easier consumption
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ [Qdrant] Error searching vectors: {str(e)}")
            return []
    
    def delete_by_paper_id(self, paper_id: int) -> bool:
        """
        Delete all vectors associated with a specific paper
        
        Called when a paper is deleted from the system to clean up
        the vector database and prevent orphaned vectors.
        
        Args:
            paper_id: ID of the paper to delete vectors for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"🗑️  [Qdrant] Deleting all vectors for paper_id={paper_id}")
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="paper_id",
                            match=MatchValue(value=paper_id)
                        )
                    ]
                )
            )
            print(f"✅ [Qdrant] Deleted vectors for paper_id={paper_id}")
            return True
            
        except Exception as e:
            print(f"❌ [Qdrant] Error deleting vectors: {str(e)}")
            return False
    
    def count_vectors(self, paper_id: Optional[int] = None) -> int:
        """
        Count vectors in collection
        
        Args:
            paper_id: Optional filter by paper ID
            
        Returns:
            Number of vectors
        """
        try:
            if paper_id:
                # Count for specific paper
                results = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="paper_id",
                                match=MatchValue(value=paper_id)
                            )
                        ]
                    ),
                    limit=1,
                    with_payload=False,
                    with_vectors=False
                )
                return results[1] if results else 0
            else:
                # Count all
                info = self.client.get_collection(self.collection_name)
                return info.points_count
                
        except Exception as e:
            print(f"Error counting vectors: {str(e)}")
            return 0
