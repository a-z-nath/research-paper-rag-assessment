"""
RAG Pipeline Service for Research Paper Query Processing

This service orchestrates the complete RAG pipeline:
1. Query embedding generation
2. Vector similarity search in Qdrant
3. Context preparation from retrieved chunks
4. LLM-based answer generation with Ollama
5. Citation extraction and formatting
"""

import logging
import time
import httpx
import json
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.services.embedding_service import EmbeddingService
from src.services.qdrant_client import QdrantClientService, SearchRequest
from src.schemas.query import Citation

logger = logging.getLogger(__name__)

@dataclass
class RAGResult:
    """Result from RAG pipeline processing"""
    answer: str
    citations: List[Citation]
    confidence: float
    processing_time: float
    context_used: str

class RAGPipeline:
    """
    RAG Pipeline for processing queries against research papers
    """
    
    def __init__(
        self,
        collection_name: str = "research_papers",
        embedding_model: str = "all-MiniLM-L6-v2",
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "llama3",
        ollama_api_key: str = "",
        max_context_length: int = 4000
    ):
        """
        Initialize RAG pipeline
        
        Args:
            collection_name: Qdrant collection name
            embedding_model: Sentence transformer model name
            ollama_base_url: Ollama server URL
            ollama_model: Ollama model name
            max_context_length: Maximum context tokens for LLM
        """
        self.collection_name = collection_name
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.ollama_api_key = ollama_api_key
        self.max_context_length = max_context_length
        
        # Initialize services
        self.embedding_service = EmbeddingService(model_name=embedding_model)
        self.qdrant_client = QdrantClientService(collection_name=collection_name)
        
        logger.info(f"RAG Pipeline initialized with model: {ollama_model}")

    async def process_query(
        self,
        question: str,
        top_k: int = 5,
        paper_filters: Optional[List[str]] = None
    ) -> RAGResult:
        """
        Process a query through the complete RAG pipeline
        
        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            paper_filters: Optional list of paper IDs to filter search
            
        Returns:
            RAGResult with answer, citations, and metadata
        """
        start_time = time.time()
        
        logger.info(f"Processing RAG query: {question[:100]}...")
        
        try:
            # 1. Generate query embedding
            query_embedding = self.embedding_service.encode_single(question)
            
            # 2. Search for relevant chunks
            chunks = await self._search_relevant_chunks(
                query_embedding, top_k, paper_filters
            )
            
            if not chunks:
                return RAGResult(
                    answer="I couldn't find any relevant information to answer your question.",
                    citations=[],
                    confidence=0.0,
                    processing_time=time.time() - start_time,
                    context_used=""
                )
            
            # 3. Prepare context and citations
            context, citations = self._prepare_context_and_citations(chunks)
            
            # 4. Generate answer with LLM
            answer, confidence = await self._generate_answer(question, context)
            
            processing_time = time.time() - start_time
            
            logger.info(f"RAG query processed in {processing_time:.2f}s")
            
            return RAGResult(
                answer=answer,
                citations=citations,
                confidence=confidence,
                processing_time=processing_time,
                context_used=context
            )
            
        except Exception as e:
            logger.error(f"RAG processing failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"RAG processing failed: {str(e)}")

    async def _search_relevant_chunks(
        self,
        query_embedding,
        top_k: int,
        paper_filters: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks in Qdrant
        
        Args:
            query_embedding: Query vector embedding
            top_k: Number of chunks to retrieve
            paper_filters: Optional paper ID filters
            
        Returns:
            List of relevant chunks with metadata
        """
        # Build filter conditions compatible with QdrantClientService._build_filter
        # If paper_filters is provided, use the 'any' key so Qdrant Match(any=...) is built.
        filter_conditions = {}
        if paper_filters:
            # Ensure all ids are strings
            filter_conditions["paper_id"] = {"any": [str(pid) for pid in paper_filters]}
        
        # Create search request
        search_request = SearchRequest(
            query_vector=query_embedding,
            collection_name=self.collection_name,
            top_k=top_k,
            score_threshold=0.0,  # Minimum relevance threshold
            filter_conditions=filter_conditions,
            return_vectors=False
        )
        
        # Perform search
        search_results = await self.qdrant_client.search_similar(search_request)
        
        # Convert to chunk format
        chunks = []
        for result in search_results:
            chunk = {
                "chunk_id": result.id,
                "content": result.payload.get("content_preview", ""),
                "paper_id": result.payload.get("paper_id"),
                "paper_title": result.payload.get("paper_title"),
                "section_name": result.payload.get("section_name"),
                "relevance_score": result.score,
                "page": result.payload.get("page", None)
            }
            chunks.append(chunk)
        
        logger.info(f"Retrieved {len(chunks)} relevant chunks")
        return chunks

    def _prepare_context_and_citations(
        self,
        chunks: List[Dict[str, Any]]
    ) -> tuple[str, List[Citation]]:
        """
        Prepare context string and citations from retrieved chunks
        
        Args:
            chunks: Retrieved chunks with metadata
            
        Returns:
            Tuple of (context_string, citations_list)
        """
        context_parts = []
        citations = []
        
        for i, chunk in enumerate(chunks, 1):
            # Add to context
            context_part = f"[{i}] {chunk['content']}"
            context_parts.append(context_part)
            
            # Create citation
            citation = Citation(
                paper_id=chunk["paper_id"],
                chunk_id=chunk["chunk_id"],
                paper_title=chunk["paper_title"],
                section=chunk["section_name"],
                snippet=chunk["content"][:300],  # Truncate for display
                page=chunk.get("page"),
                relevance_score=chunk["relevance_score"]
            )
            citations.append(citation)
        
        # Combine context (truncate if too long)
        context = "\n\n".join(context_parts)
        if len(context) > self.max_context_length:
            context = context[:self.max_context_length] + "..."
        
        return context, citations

    async def _generate_answer(
        self,
        question: str,
        context: str
    ) -> tuple[str, float]:
        """
        Generate answer using Ollama LLM with fallback handling
        
        Args:
            question: User's question
            context: Retrieved context from papers
            
        Returns:
            Tuple of (answer, confidence_score)
        """
        # Prepare prompt
        prompt = f"""Based on the following research paper excerpts, please answer the question. Be precise and cite relevant information from the provided context.

Context from research papers:
{context}

Question: {question}

Please provide a comprehensive answer based solely on the context above. Focus on what the research papers say about this topic."""

        try:
            # Check if we can connect to Ollama first
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Test connection
                try:
                    health_response = await client.get(f"{self.ollama_base_url}/api/tags")
                    if health_response.status_code != 200:
                        logger.warning("Ollama not available, using fallback response")
                        return self._generate_fallback_answer(question, context)
                except (httpx.ConnectError, httpx.TimeoutException):
                    logger.warning("Cannot connect to Ollama, using fallback response")
                    return self._generate_fallback_answer(question, context)
                
                # If connection is good, proceed with generation
                headers = {}
                if self.ollama_api_key:
                    headers["Authorization"] = f"Bearer {self.ollama_api_key}"
                
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False
                    },
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Ollama request failed with status {response.status_code}: {response.text}")
                    return self._generate_fallback_answer(question, context)
                
                result = response.json()
                answer = result.get("response", "").strip()
                
                if not answer:
                    logger.warning("Empty response from Ollama, using fallback")
                    return self._generate_fallback_answer(question, context)
                
                # Clean up common unwanted sections from LLM responses
                answer = self._clean_llm_response(answer)
                
                # Calculate confidence based on response length and context relevance
                confidence = min(0.9, len(answer) / 500 + 0.3)  # Simple heuristic
                
                logger.info("Successfully generated answer using Ollama")
                return answer, confidence
                
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            logger.info("Falling back to context-based answer")
            return self._generate_fallback_answer(question, context)

    def _clean_llm_response(self, answer: str) -> str:
        """
        Clean unwanted sections from LLM responses
        
        Args:
            answer: Raw LLM response
            
        Returns:
            Cleaned response
        """
        # Remove "Information Missing from the Context" sections
        patterns_to_remove = [
            r'\n\n.*?Information Missing from the Context.*?(?=\n\n|\Z)',
            r'\n\n.*?Significant missing information includes:.*?(?=\n\n|\Z)',
            r'\n\n.*?Missing information:.*?(?=\n\n|\Z)',
            r'\n\n.*?However, the provided context lacks.*?(?=\n\n|\Z)'
        ]
        
        cleaned_answer = answer
        for pattern in patterns_to_remove:
            cleaned_answer = re.sub(pattern, '', cleaned_answer, flags=re.DOTALL | re.IGNORECASE)
        
        # Clean up extra whitespace
        cleaned_answer = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_answer)
        cleaned_answer = cleaned_answer.strip()
        
        return cleaned_answer

    def _generate_fallback_answer(
        self,
        question: str,
        context: str
    ) -> tuple[str, float]:
        """
        Generate a fallback answer when Ollama is not available
        
        Args:
            question: User's question
            context: Retrieved context from papers
            
        Returns:
            Tuple of (answer, confidence_score)
        """
        if not context:
            return (
                "I couldn't find any relevant information to answer your question. Please try rephrasing your question or ensure that relevant papers have been uploaded.",
                0.1
            )
        
        # Create a simple context-based answer
        answer = f"""Based on the available research papers, I found the following relevant information:

{context[:1000]}...

Note: This is a summarized response from the available research papers. For a more comprehensive AI-generated answer, please ensure the language model service is properly configured and running."""
        
        # Lower confidence for fallback answers
        confidence = 0.4
        
        return answer, confidence

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if all pipeline components are healthy
        
        Returns:
            Dict with health status of each component
        """
        health_status = {
            "overall_healthy": True,
            "components": {}
        }
        
        try:
            # Test Qdrant connection
            qdrant_healthy = await self.qdrant_client.ensure_collection_exists(self.collection_name)
            health_status["components"]["qdrant"] = {
                "healthy": qdrant_healthy,
                "message": "Connected" if qdrant_healthy else "Connection failed"
            }
        except Exception as e:
            health_status["components"]["qdrant"] = {
                "healthy": False,
                "message": f"Error: {str(e)}"
            }
            health_status["overall_healthy"] = False
        
        try:
            # Test Ollama connection
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags")
                ollama_healthy = response.status_code == 200
                health_status["components"]["ollama"] = {
                    "healthy": ollama_healthy,
                    "message": "Connected" if ollama_healthy else f"HTTP {response.status_code}"
                }
        except Exception as e:
            health_status["components"]["ollama"] = {
                "healthy": False,
                "message": f"Connection error: {str(e)}"
            }
            # Don't mark overall as unhealthy - we have fallback
            logger.warning("Ollama not available, but fallback mechanism will be used")
        
        try:
            # Test embedding service
            test_embedding = self.embedding_service.encode_single("test")
            embedding_healthy = test_embedding is not None
            health_status["components"]["embedding_service"] = {
                "healthy": embedding_healthy,
                "message": "Working" if embedding_healthy else "Failed to generate embeddings"
            }
            if not embedding_healthy:
                health_status["overall_healthy"] = False
        except Exception as e:
            health_status["components"]["embedding_service"] = {
                "healthy": False,
                "message": f"Error: {str(e)}"
            }
            health_status["overall_healthy"] = False
        
        return health_status