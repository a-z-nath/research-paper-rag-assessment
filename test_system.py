#!/usr/bin/env python3
"""
Comprehensive test script for the Research Paper RAG system.
Tests all major functionality including upload, query, and analytics.
"""

import requests
import json
import time
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000"

class RAGSystemTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.uploaded_papers = []
        self.test_results = {
            "health": False,
            "upload": False,
            "query": False,
            "analytics": False,
            "total_score": 0
        }

    def print_header(self, title: str):
        """Print a formatted test section header."""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}")

    def print_result(self, test_name: str, success: bool, details: str = ""):
        """Print formatted test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")

    def test_health(self) -> bool:
        """Test if the API is running and healthy."""
        self.print_header("Health Check")
        
        try:
            # Basic health check
            response = requests.get(f"{self.base_url}/health", timeout=10)
            basic_health = response.status_code == 200
            self.print_result("API Health", basic_health, f"Status: {response.status_code}")
            
            if basic_health:
                health_data = response.json()
                print(f"    Response: {health_data}")
            
            # RAG pipeline health
            try:
                rag_response = requests.get(f"{self.base_url}/api/rag/health", timeout=10)
                rag_health = rag_response.status_code == 200
                self.print_result("RAG Pipeline Health", rag_health)
                
                if rag_health:
                    rag_data = rag_response.json()
                    print(f"    RAG Status: {rag_data}")
            except Exception as e:
                self.print_result("RAG Pipeline Health", False, f"Error: {e}")
                rag_health = False
            
            overall_health = basic_health and rag_health
            self.test_results["health"] = overall_health
            return overall_health
            
        except requests.exceptions.RequestException as e:
            self.print_result("API Connection", False, f"Cannot connect: {e}")
            return False

    def test_paper_upload(self) -> bool:
        """Test paper upload functionality."""
        self.print_header("Paper Upload")
        
        # Check for sample papers
        sample_dir = Path("sample_papers")
        if not sample_dir.exists():
            self.print_result("Sample Papers Directory", False, "sample_papers/ not found")
            return False
        
        pdf_files = list(sample_dir.glob("*.pdf"))
        if not pdf_files:
            self.print_result("Sample PDF Files", False, "No PDF files in sample_papers/")
            return False
        
        self.print_result("Sample Papers Found", True, f"{len(pdf_files)} PDF files detected")
        
        # Test single file upload
        test_file = pdf_files[0]
        try:
            with open(test_file, 'rb') as f:
                files = {'files': (test_file.name, f, 'application/pdf')}
                response = requests.post(
                    f"{self.base_url}/api/papers/upload",
                    files=files,
                    timeout=60
                )
            
            if response.status_code == 200:
                upload_data = response.json()
                if upload_data.get('uploaded_papers'):
                    paper_id = upload_data['uploaded_papers'][0]['paper_id']
                    self.uploaded_papers.append(paper_id)
                    self.print_result("Single File Upload", True, f"Paper ID: {paper_id}")
                    
                    # Test batch upload (up to 3 files to avoid timeout)
                    batch_files = pdf_files[1:4] if len(pdf_files) > 3 else pdf_files[1:]
                    if batch_files:
                        try:
                            file_data = []
                            for file_path in batch_files:
                                with open(file_path, 'rb') as f:
                                    file_data.append(('files', (file_path.name, f.read(), 'application/pdf')))
                            
                            batch_response = requests.post(
                                f"{self.base_url}/api/papers/upload",
                                files=file_data,
                                timeout=120
                            )
                            
                            if batch_response.status_code == 200:
                                batch_data = batch_response.json()
                                batch_papers = batch_data.get('uploaded_papers', [])
                                for paper in batch_papers:
                                    self.uploaded_papers.append(paper['paper_id'])
                                
                                self.print_result("Batch Upload", True, f"{len(batch_papers)} papers uploaded")
                            else:
                                self.print_result("Batch Upload", False, f"Status: {batch_response.status_code}")
                        
                        except Exception as e:
                            self.print_result("Batch Upload", False, f"Error: {e}")
                    
                    self.test_results["upload"] = True
                    return True
                else:
                    self.print_result("Single File Upload", False, "No papers in response")
                    return False
            else:
                self.print_result("Single File Upload", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_result("Upload Process", False, f"Error: {e}")
            return False

    def test_query_system(self) -> bool:
        """Test the RAG query system."""
        self.print_header("Query System")
        
        if not self.uploaded_papers:
            self.print_result("Papers Available", False, "No papers for querying")
            return False
        
        # Test queries from different complexity levels
        test_queries = [
            {
                "question": "What is the main contribution of this paper?",
                "description": "Basic contribution query",
                "top_k": 5
            },
            {
                "question": "What methodology was used in the research?",
                "description": "Methodology-focused query",
                "top_k": 3
            },
            {
                "question": "What are the key findings and results?",
                "description": "Results-focused query",
                "top_k": 5
            }
        ]
        
        successful_queries = 0
        total_response_time = 0
        
        for i, query in enumerate(test_queries, 1):
            try:
                start_time = time.time()
                
                payload = {
                    "question": query["question"],
                    "top_k": query["top_k"]
                }
                
                response = requests.post(
                    f"{self.base_url}/api/query",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                response_time = time.time() - start_time
                total_response_time += response_time
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get('answer', '')
                    citations = data.get('citations', [])
                    confidence = data.get('confidence', 0)
                    
                    success = len(answer) > 50 and len(citations) > 0
                    self.print_result(
                        f"Query {i}: {query['description']}", 
                        success,
                        f"Answer: {len(answer)} chars, Citations: {len(citations)}, Time: {response_time:.2f}s"
                    )
                    
                    if success:
                        successful_queries += 1
                        print(f"    Preview: {answer[:100]}...")
                        print(f"    Confidence: {confidence}")
                else:
                    self.print_result(f"Query {i}", False, f"Status: {response.status_code}")
                    
            except Exception as e:
                self.print_result(f"Query {i}", False, f"Error: {e}")
        
        # Test query history
        try:
            history_response = requests.get(f"{self.base_url}/api/queries/history?limit=5")
            if history_response.status_code == 200:
                history = history_response.json()
                self.print_result("Query History", True, f"{len(history)} queries in history")
            else:
                self.print_result("Query History", False, f"Status: {history_response.status_code}")
        except Exception as e:
            self.print_result("Query History", False, f"Error: {e}")
        
        query_success = successful_queries >= len(test_queries) * 0.75  # 75% success rate
        avg_response_time = total_response_time / len(test_queries) if test_queries else 0
        
        print(f"\n📊 Query Performance Summary:")
        print(f"    Successful queries: {successful_queries}/{len(test_queries)}")
        print(f"    Average response time: {avg_response_time:.2f}s")
        
        self.test_results["query"] = query_success
        return query_success

    def test_analytics(self) -> bool:
        """Test analytics endpoints."""
        self.print_header("Analytics")
        
        try:
            # Test popular topics
            analytics_response = requests.get(f"{self.base_url}/api/analytics/popular?limit=10")
            
            if analytics_response.status_code == 200:
                analytics_data = analytics_response.json()
                topics = analytics_data.get('topics', [])
                
                self.print_result("Popular Topics", True, f"{len(topics)} topics found")
                
                if topics:
                    print(f"    Top topics:")
                    for i, topic in enumerate(topics[:3], 1):
                        print(f"      {i}. {topic.get('topic', 'N/A')} ({topic.get('query_count', 0)} queries)")
                
                self.test_results["analytics"] = True
                return True
            else:
                self.print_result("Analytics API", False, f"Status: {analytics_response.status_code}")
                return False
                
        except Exception as e:
            self.print_result("Analytics", False, f"Error: {e}")
            return False

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results."""
        print("🚀 Starting Comprehensive RAG System Test Suite")
        print(f"Testing against: {self.base_url}")
        
        start_time = time.time()
        
        # Run all test categories
        tests = [
            ("Health Check", self.test_health),
            ("Paper Upload", self.test_paper_upload),
            ("Query System", self.test_query_system),
            ("Analytics", self.test_analytics)
        ]
        
        results = {}
        total_score = 0
        max_score = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
                if result:
                    total_score += 1
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results[test_name] = False
        
        # Calculate final score
        percentage = (total_score / max_score) * 100
        
        # Print final summary
        self.print_header("Test Summary")
        print(f"📊 Overall Score: {total_score}/{max_score} ({percentage:.1f}%)")
        print(f"⏱️  Total Runtime: {time.time() - start_time:.2f} seconds")
        print(f"📝 Papers Uploaded: {len(self.uploaded_papers)}")
        
        print(f"\n📋 Detailed Results:")
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} {test_name}")
        
        # Recommendation based on score
        if percentage >= 90:
            print(f"\n🌟 Excellent! System is production-ready")
        elif percentage >= 75:
            print(f"\n✅ Good! System is functional with minor issues")
        elif percentage >= 50:
            print(f"\n⚠️  Acceptable but needs improvement")
        else:
            print(f"\n❌ System has significant issues requiring attention")
        
        return {
            "total_score": total_score,
            "max_score": max_score,
            "percentage": percentage,
            "results": results,
            "uploaded_papers": self.uploaded_papers,
            "runtime": time.time() - start_time
        }

def main():
    """Main function to run the test suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Research Paper RAG system")
    parser.add_argument("--url", default=BASE_URL, help="Base URL of the API")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    
    args = parser.parse_args()
    
    tester = RAGSystemTester(args.url)
    
    if args.quick:
        # Quick health check only
        print("🏃 Running quick health check...")
        health_ok = tester.test_health()
        sys.exit(0 if health_ok else 1)
    else:
        # Full test suite
        results = tester.run_comprehensive_test()
        
        # Exit with appropriate code
        success_threshold = 75  # 75% pass rate required
        sys.exit(0 if results["percentage"] >= success_threshold else 1)

if __name__ == "__main__":
    main()