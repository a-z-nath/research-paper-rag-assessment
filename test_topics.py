#!/usr/bin/env python3
"""
Test script for the new TF-IDF based topic analytics endpoint
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_tfidf_topic_analytics():
    """Test the new TF-IDF topic analytics endpoint"""
    
    print("Testing TF-IDF based topic analytics...")
    
    # Test first time processing (should process all queries)
    print("\n--- First time processing (force_rebuild=True) ---")
    response = requests.get(f"{BASE_URL}/api/analytics/popular?force_rebuild=true")
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Topics found: {len(data.get('topics', []))}")
        
        metadata = data.get('metadata', {})
        print(f"Total queries processed: {metadata.get('total_queries_processed')}")
        print(f"Topics in database: {metadata.get('topics_in_database')}")
        print(f"Processing time: {metadata.get('processing_time'):.3f}s")
        print(f"Cache hit: {metadata.get('cache_hit')}")
        print(f"Queries processed this request: {metadata.get('queries_processed_this_request')}")
        print(f"Topics updated this request: {metadata.get('topics_updated_this_request')}")
        
        # Show top 3 topics with TF-IDF scores
        for i, topic in enumerate(data.get('topics', [])[:3]):
            print(f"\nTopic {i+1}:")
            print(f"  Topic: {topic.get('topic')}")
            print(f"  Query count: {topic.get('query_count')}")
            print(f"  TF-IDF score: {topic.get('tfidf_score')}")
            print(f"  Percentage: {topic.get('percentage')}%")
            print(f"  Sample questions: {topic.get('sample_questions')}")
            print(f"  Last updated: {topic.get('last_updated')}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return
    
    # Wait a moment and test again (should be cache hit)
    print("\n--- Second call (should be cache hit) ---")
    response = requests.get(f"{BASE_URL}/api/analytics/popular")
    if response.status_code == 200:
        data = response.json()
        metadata = data.get('metadata', {})
        print(f"Processing time: {metadata.get('processing_time'):.3f}s")
        print(f"Cache hit: {metadata.get('cache_hit')}")
        print(f"Queries processed this request: {metadata.get('queries_processed_this_request')}")
        
        if metadata.get('cache_hit'):
            print("✅ Cache working correctly!")
        else:
            print("⚠️  Expected cache hit but got processing")
    else:
        print(f"Error: {response.status_code} - {response.text}")
    
    # Test with different limit
    print("\n--- Test with limit=5 ---")
    response = requests.get(f"{BASE_URL}/api/analytics/popular?limit=5")
    if response.status_code == 200:
        data = response.json()
        print(f"Topics returned: {len(data.get('topics', []))}")
        topics = data.get('topics', [])
        if topics:
            print(f"Top topic: {topics[0].get('topic')} (TF-IDF: {topics[0].get('tfidf_score')})")
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_tfidf_topic_analytics()