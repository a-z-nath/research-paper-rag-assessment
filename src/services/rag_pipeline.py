"""
RAG Pipeline - orchestrates retrieval and generation
"""
import time
import requests
from typing import List, Dict, Tuple
from services.embedding_service import EmbeddingService
from services.qdrant_client import QdrantService
from services.llm_service import LLMService


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline"""
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        qdrant_service: QdrantService,
        llm_service: LLMService,
        max_context_length: int = 2000
    ):
        """
        Initialize RAG pipeline
        
        Args:
            embedding_service: Service for generating embeddings
            qdrant_service: Service for vector search
            llm_service: Text generation service (Google Gemini)
            max_context_length: Maximum context length in tokens
        """
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service
        self.llm_service = llm_service
        self.max_context_length = max_context_length
    
    def query(
        self,
        question: str,
        top_k: int = 5,
        paper_ids: List[int] = None
    ) -> Dict:
        """
        Process a query through the RAG pipeline
        
        RAG (Retrieval-Augmented Generation) workflow:
        1. Embed the user's question into a vector
        2. Retrieve most relevant chunks from vector DB
        3. Assemble context from retrieved chunks
        4. Generate answer using LLM with context
        5. Calculate confidence and prepare citations
        
        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            paper_ids: Optional filter by paper IDs
            
        Returns:
            Dict with answer, citations, confidence, etc.
        """
        start_time = time.time()
        print(f"🔄 [RAG] Starting RAG pipeline...")
        
        try:
            # Step 1: Embed the question into vector space
            print(f"   Step 1: Embedding question...")
            # Optionally expand query for better retrieval
            expanded_question = self._expand_query(question)
            query_embedding = self.embedding_service.embed_text(expanded_question)
            print(f"   ✅ Question embedded ({len(query_embedding)} dimensions)")
            
            # Step 2: Retrieve relevant chunks using vector similarity
            # Retrieve more candidates than needed for better quality filtering
            print(f"   Step 2: Searching for top {top_k * 2} relevant chunks...")
            search_results = self.qdrant_service.search(
                query_vector=query_embedding,
                top_k=top_k * 2,  # Retrieve 2x candidates for filtering
                paper_ids=paper_ids,
                score_threshold=0.3  # Filter out very low relevance chunks
            )
            print(f"   ✅ Found {len(search_results)} relevant chunks")
            
            # Filter and re-rank results for better quality
            search_results = self._filter_and_rerank(search_results, question)
            search_results = search_results[:top_k]  # Keep only top K after filtering
            print(f"   ✅ After filtering: {len(search_results)} high-quality chunks")
            
            if not search_results:
                print(f"   ⚠️  No relevant chunks found")
                return {
                    'answer': "I couldn't find any relevant information in the papers to answer this question.",
                    'citations': [],
                    'sources_used': [],
                    'confidence': 0.0,
                    'response_time': time.time() - start_time
                }
            
            # Step 3: Assemble context and prepare citations
            print(f"   Step 3: Preparing context from retrieved chunks...")
            context, citations = self._prepare_context(search_results)
            print(f"   ✅ Context prepared ({len(context)} chars, {len(citations)} citations)")
            
            # Step 4: Generate answer using Gemini LLM
            print(f"   Step 4: Generating answer with LLM...")
            answer = self._generate_answer(question, context)
            print(f"   ✅ Answer generated")
            
            # Step 5: Calculate confidence based on relevance scores
            confidence = self._calculate_confidence(search_results)
            print(f"   Step 5: Confidence calculated: {confidence:.2%}")
            
            # Step 6: Extract unique sources used
            sources_used = list(set([c['paper_title'] for c in citations]))
            print(f"   ✅ RAG pipeline completed successfully")
            
            response_time = time.time() - start_time
            
            return {
                'answer': answer,
                'citations': citations,
                'sources_used': sources_used,
                'confidence': confidence,
                'response_time': response_time
            }
            
        except Exception as e:
            print(f"❌ [RAG] Error in RAG pipeline: {str(e)}")
            return {
                'answer': f"An error occurred while processing your query: {str(e)}",
                'citations': [],
                'sources_used': [],
                'confidence': 0.0,
                'response_time': time.time() - start_time
            }
    
    def _expand_query(self, question: str) -> str:
        """
        Expand query with context for better retrieval
        
        Adds implicit context to improve embedding quality.
        For example: "What is attention?" -> "What is attention mechanism in neural networks?"
        
        Args:
            question: Original question
            
        Returns:
            Expanded question with additional context
        """
        # Add research paper context to improve retrieval
        # This helps the embedding model understand we're looking for academic content
        expanded = f"Research paper query: {question}"
        
        # Add common research terms if not present
        question_lower = question.lower()
        if 'method' in question_lower and 'methodology' not in question_lower:
            expanded += " methodology approach"
        if 'result' in question_lower and 'findings' not in question_lower:
            expanded += " findings outcomes"
        if 'what is' in question_lower or 'define' in question_lower:
            expanded += " definition explanation"
        
        return expanded
    
    def _filter_and_rerank(self, search_results: List[Dict], question: str) -> List[Dict]:
        """
        Filter and re-rank search results for better quality
        
        Removes duplicates, filters low-quality chunks, and ensures diversity
        
        Args:
            search_results: Raw search results from vector DB
            question: Original user question
            
        Returns:
            Filtered and re-ranked results
        """
        if not search_results:
            return []
        
        # Step 1: Remove near-duplicate chunks (same paper, similar text)
        unique_results = []
        seen_texts = set()
        
        for result in search_results:
            text = result['payload'].get('text', '')
            # Use first 100 chars as fingerprint
            fingerprint = text[:100].lower().strip()
            
            if fingerprint not in seen_texts:
                seen_texts.add(fingerprint)
                unique_results.append(result)
        
        # Step 2: Boost chunks that contain question keywords
        question_words = set(question.lower().split())
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are', 'was', 'were', 'what', 'how', 'why', 'when', 'where'}
        question_keywords = question_words - stop_words
        
        for result in unique_results:
            text = result['payload'].get('text', '').lower()
            # Count keyword matches
            keyword_matches = sum(1 for word in question_keywords if word in text)
            # Boost score based on keyword matches (up to 15% boost)
            boost = min(keyword_matches * 0.03, 0.15)
            result['boosted_score'] = result['score'] * (1 + boost)
        
        # Step 3: Re-sort by boosted score
        unique_results.sort(key=lambda x: x.get('boosted_score', x['score']), reverse=True)
        
        # Step 4: Ensure diversity - don't return all chunks from same section
        diverse_results = []
        section_counts = {}
        
        for result in unique_results:
            section = result['payload'].get('section', 'Other')
            section_count = section_counts.get(section, 0)
            
            # Limit chunks per section (max 3 from same section)
            if section_count < 3:
                diverse_results.append(result)
                section_counts[section] = section_count + 1
        
        return diverse_results
    
    def _prepare_context(self, search_results: List[Dict]) -> Tuple[str, List[Dict]]:
        """
        Prepare context from search results and create citations
        
        Args:
            search_results: Results from vector search
            
        Returns:
            Tuple of (context_string, citations_list)
        """
        context_parts = []
        citations = []
        
        for i, result in enumerate(search_results):
            payload = result['payload']
            score = result.get('boosted_score', result['score'])  # Use boosted score if available
            
            # Build context chunk with rich source info
            chunk_text = payload.get('text', '')
            title = payload.get('title', 'Unknown')
            page = payload.get('page', 0)
            section = payload.get('section', 'Unknown')
            authors = payload.get('authors', 'Unknown')
            
            # Add to context with reference number and metadata for better citation
            # Include source info so LLM knows where info comes from
            context_part = f"""[Reference {i+1}]
Source: "{title}" (Page {page}, Section: {section})
Content: {chunk_text}"""
            context_parts.append(context_part)
            
            # Create detailed citation with all metadata
            citations.append({
                'paper_title': title,
                'authors': authors,
                'section': section,
                'page': page,
                'relevance_score': round(score, 3),
                'chunk_text': chunk_text[:300] + '...' if len(chunk_text) > 300 else chunk_text,
                'reference_number': i + 1
            })
        
        # Join context, limit by length
        full_context = '\n\n'.join(context_parts)
        
        # Truncate if too long (rough estimate: 4 chars = 1 token)
        max_chars = self.max_context_length * 4
        if len(full_context) > max_chars:
            full_context = full_context[:max_chars] + '...'
        
        return full_context, citations
    
    def _generate_answer(self, question: str, context: str) -> str:
        """
        Generate answer using Gemini LLM with carefully crafted prompt
        
        This method constructs a prompt that:
        - Provides clear instructions to the LLM
        - Includes retrieved context from papers
        - Enforces citation requirements
        - Prevents hallucination (making up information)
        
        Args:
            question: User's question
            context: Retrieved context from vector search
            
        Returns:
            Generated answer from LLM
        """
        # Construct prompt with instructions (prompt engineering is critical for quality answers)
        prompt = f"""You are an expert research assistant with deep knowledge of academic papers. Your task is to provide accurate, well-cited answers based ONLY on the provided context.

CONTEXT FROM RESEARCH PAPERS:
{context}

USER QUESTION: {question}

INSTRUCTIONS FOR YOUR ANSWER:
1. **Accuracy First**: Base your answer STRICTLY on the provided context. If information is insufficient, clearly state what's missing.
2. **Citation Style**: When referencing information, cite using format [Reference #] (e.g., "According to [1], the transformer architecture...").
3. **Be Specific**: Include specific details like numbers, methods, results from the papers when available.
4. **No Hallucination**: Never invent information, statistics, or citations not present in the context.
5. **Structured Response**: Organize your answer clearly with:
   - Direct answer to the question
   - Supporting evidence from papers with citations
   - Any caveats or limitations based on available context
6. **Technical Precision**: Use precise academic language and maintain technical accuracy.
7. **Uncertainty Acknowledgment**: If the context is ambiguous or incomplete, explicitly say so.

ANSWER:"""
        
        try:
            # Call LLM service to generate answer
            return self.llm_service.generate_text(prompt)
        except Exception as e:
            print(f"❌ [RAG] Error generating with LLM service: {e}")
            return f"Error generating answer: {e}"
    
    def _calculate_confidence(self, search_results: List[Dict]) -> float:
        """
        Calculate confidence score based on multiple factors
        
        Considers:
        - Relevance scores (higher = better match)
        - Score distribution (tight cluster = high confidence)
        - Number of results (more agreement = higher confidence)
        - Diversity of sources (multiple papers = higher confidence)
        
        Args:
            search_results: Results from vector search
            
        Returns:
            Confidence score between 0 and 1
        """
        if not search_results:
            return 0.0
        
        # Factor 1: Average relevance score (60% weight)
        top_scores = [r.get('boosted_score', r['score']) for r in search_results[:3]]
        avg_score = sum(top_scores) / len(top_scores)
        score_factor = avg_score * 0.6
        
        # Factor 2: Score consistency (20% weight)
        # If top results have similar scores, we're more confident
        if len(search_results) >= 3:
            score_std = (max(top_scores) - min(top_scores))
            # Lower std = higher consistency = higher confidence
            consistency_factor = (1 - min(score_std, 0.3) / 0.3) * 0.2
        else:
            consistency_factor = 0.1
        
        # Factor 3: Result count (10% weight)
        # More high-quality results = higher confidence
        count_factor = min(len(search_results) / 5, 1.0) * 0.1
        
        # Factor 4: Source diversity (10% weight)
        # Multiple papers agreeing = higher confidence
        unique_papers = len(set(r['payload'].get('title', '') for r in search_results))
        diversity_factor = min(unique_papers / 3, 1.0) * 0.1
        
        # Combine all factors
        confidence = score_factor + consistency_factor + count_factor + diversity_factor
        
        # Normalize to 0-1 range
        confidence = min(max(confidence, 0.0), 1.0)
        
        return round(confidence, 3)
