#!/usr/bin/env python3
"""
Test script for the Research Paper RAG API

This script tests the basic functionality of the API endpoints.
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_api_health():
    """Test the API health check endpoint"""
    print("Testing API health check...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"API health status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"API health check failed: {e}")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    print("Testing root endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Root endpoint status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Root endpoint failed: {e}")
        return False

def test_paper_upload():
    """Test paper upload functionality"""
    print("Testing paper upload...")
    
    # Find a sample PDF file
    sample_dir = Path("../sample_papers")
    if not sample_dir.exists():
        sample_dir = Path("./sample_papers")
    
    if not sample_dir.exists():
        print("No sample_papers directory found. Skipping upload test.")
        return False
    
    pdf_files = list(sample_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in sample_papers. Skipping upload test.")
        return False
    
    test_file = pdf_files[0]
    print(f"Uploading: {test_file.name}")
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/api/papers/upload", files=files)
        
        print(f"Upload status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            paper_id = result.get('paper_id')
            print(f"Paper uploaded successfully with ID: {paper_id}")
            return paper_id
        else:
            print(f"Upload failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Upload test failed: {e}")
        return False

def test_list_papers():
    """Test listing papers"""
    print("Testing list papers...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/papers")
        print(f"List papers status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Found {result.get('total', 0)} papers")
            papers = result.get('papers', [])
            for paper in papers[:3]:  # Show first 3
                print(f"  - {paper.get('title', 'No title')} ({paper.get('status', 'unknown')})")
            return True
        else:
            print(f"List papers failed: {response.json()}")
            return False
            
    except Exception as e:
        print(f"List papers test failed: {e}")
        return False

def test_get_paper(paper_id):
    """Test getting a specific paper"""
    if not paper_id:
        print("No paper ID provided, skipping get paper test")
        return False
        
    print(f"Testing get paper for ID: {paper_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/api/papers/{paper_id}")
        print(f"Get paper status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Paper title: {result.get('title', 'No title')}")
            print(f"Paper status: {result.get('status', 'unknown')}")
            return True
        else:
            print(f"Get paper failed: {response.json()}")
            return False
            
    except Exception as e:
        print(f"Get paper test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("Research Paper RAG API Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Health check
    total_tests += 1
    if test_health_check():
        tests_passed += 1
    print()
    
    # Test 2: API health check
    total_tests += 1
    if test_api_health():
        tests_passed += 1
    print()
    
    # Test 3: Root endpoint
    total_tests += 1
    if test_root_endpoint():
        tests_passed += 1
    print()
    
    # Test 4: List papers (should work even if empty)
    total_tests += 1
    if test_list_papers():
        tests_passed += 1
    print()
    
    # Test 5: Upload paper (optional - requires sample files)
    paper_id = test_paper_upload()
    if paper_id:
        tests_passed += 1
        
        # Test 6: Get specific paper (only if upload succeeded)
        if test_get_paper(paper_id):
            tests_passed += 1
        total_tests += 1
    
    total_tests += 1  # Count upload test even if it fails
    
    print("=" * 50)
    print(f"Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed!")
    elif tests_passed > total_tests // 2:
        print("⚠️  Most tests passed. Some failures expected during development.")
    else:
        print("❌ Many tests failed. Check your API server and configuration.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()