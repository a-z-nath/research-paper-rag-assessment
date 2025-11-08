"""
Query Cache Service for RAG System

Implements caching for repeated queries to speed up response times.
Uses in-memory cache with TTL and query normalization.
"""
import hashlib
import json
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta


class QueryCache:
    """
    Cache for query responses with TTL and hit/miss tracking
    """
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Initialize query cache
        
        Args:
            ttl_seconds: Time-to-live for cached entries (default: 1 hour)
            max_size: Maximum number of entries to store
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def _normalize_query(self, question: str, top_k: int = 5, paper_ids: Optional[list] = None) -> str:
        """
        Normalize query parameters to create a consistent cache key
        
        Args:
            question: The query question
            top_k: Number of results
            paper_ids: Optional list of paper IDs to filter
            
        Returns:
            Normalized cache key
        """
        # Normalize question (lowercase, strip whitespace, remove extra spaces)
        normalized_question = ' '.join(question.lower().strip().split())
        
        # Sort paper_ids for consistency
        sorted_paper_ids = sorted(paper_ids) if paper_ids else None
        
        # Create cache key structure
        key_data = {
            'question': normalized_question,
            'top_k': top_k,
            'paper_ids': sorted_paper_ids
        }
        
        # Generate hash of the normalized data
        key_json = json.dumps(key_data, sort_keys=True)
        cache_key = hashlib.sha256(key_json.encode()).hexdigest()
        
        return cache_key
    
    def get(self, question: str, top_k: int = 5, paper_ids: Optional[list] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response for a query
        
        Args:
            question: The query question
            top_k: Number of results
            paper_ids: Optional list of paper IDs to filter
            
        Returns:
            Cached response if available and not expired, None otherwise
        """
        cache_key = self._normalize_query(question, top_k, paper_ids)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Check if entry has expired
            if time.time() < entry['expires_at']:
                self.hits += 1
                entry['hit_count'] += 1
                entry['last_accessed'] = datetime.now()
                return entry['response']
            else:
                # Entry expired, remove it
                del self.cache[cache_key]
        
        self.misses += 1
        return None
    
    def set(self, question: str, response: Dict[str, Any], top_k: int = 5, paper_ids: Optional[list] = None):
        """
        Cache a query response
        
        Args:
            question: The query question
            response: The response to cache
            top_k: Number of results
            paper_ids: Optional list of paper IDs to filter
        """
        cache_key = self._normalize_query(question, top_k, paper_ids)
        
        # Evict oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        # Store in cache with expiration time
        self.cache[cache_key] = {
            'response': response,
            'created_at': datetime.now(),
            'last_accessed': datetime.now(),
            'expires_at': time.time() + self.ttl_seconds,
            'hit_count': 0,
            'original_question': question,
            'top_k': top_k,
            'paper_ids': paper_ids
        }
    
    def _evict_oldest(self):
        """Evict the least recently accessed entry"""
        if not self.cache:
            return
        
        # Find entry with oldest last_accessed time
        oldest_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k]['last_accessed']
        )
        
        del self.cache[oldest_key]
        self.evictions += 1
    
    def clear(self):
        """Clear all cached entries"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        # Get entry statistics
        entries = []
        for key, entry in self.cache.items():
            time_to_live = entry['expires_at'] - time.time()
            entries.append({
                'question': entry['original_question'][:100],  # Truncate for display
                'hit_count': entry['hit_count'],
                'created_at': entry['created_at'].isoformat(),
                'ttl_seconds': int(time_to_live)
            })
        
        # Sort by hit count (most accessed first)
        entries.sort(key=lambda x: x['hit_count'], reverse=True)
        
        return {
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'total_hits': self.hits,
            'total_misses': self.misses,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'evictions': self.evictions,
            'ttl_seconds': self.ttl_seconds,
            'top_cached_queries': entries[:10]  # Top 10 most accessed
        }
    
    def invalidate_by_paper(self, paper_id: int):
        """
        Invalidate all cached queries that involve a specific paper
        
        Args:
            paper_id: The paper ID to invalidate
        """
        keys_to_remove = []
        
        for key, entry in self.cache.items():
            paper_ids = entry.get('paper_ids')
            # If no paper_ids filter, query includes all papers
            # If paper_ids includes this paper, invalidate
            if paper_ids is None or paper_id in paper_ids:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
    
    def cleanup_expired(self):
        """Remove all expired entries from cache"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time >= entry['expires_at']
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
