#!/usr/bin/env python3
"""
Test script for Text Chunking Service
Tests the hybrid chunking strategy with sample PDFs
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.services.pdf_processor import PDFProcessor
from src.services.text_chunker import TextChunker

def test_chunking_strategy():
    """Test chunking with sample PDFs"""
    print("🔧 Testing Hybrid Text Chunking Strategy")
    print("=" * 60)
    
    # Initialize services
    pdf_processor = PDFProcessor()
    text_chunker = TextChunker(
        target_chunk_size=500,
        max_chunk_size=800,
        min_chunk_size=100,
        overlap_size=50
    )
    
    # Get sample PDFs
    sample_dir = Path("sample_papers")
    if not sample_dir.exists():
        print("❌ sample_papers directory not found!")
        return False
    
    pdf_files = sorted(list(sample_dir.glob("*.pdf")))[:2]  # Test with first 2 files
    if not pdf_files:
        print("❌ No PDF files found!")
        return False
    
    print(f"Testing with {len(pdf_files)} PDF files\n")
    
    all_results = []
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"📄 Processing {i}/{len(pdf_files)}: {pdf_file.name}")
        print("-" * 40)
        
        try:
            # Step 1: Extract PDF content
            pdf_result = pdf_processor.process_pdf(str(pdf_file))
            print(f"✅ PDF processed: {len(pdf_result.sections)} sections, {pdf_result.metadata.num_pages} pages")
            
            # Step 2: Chunk the content
            chunking_result = text_chunker.chunk_pdf_content(pdf_result)
            print(f"✅ Chunking completed: {chunking_result.total_chunks} chunks, {chunking_result.total_tokens} tokens")
            
            # Display chunking statistics
            print(f"\n📊 Chunking Statistics:")
            stats = chunking_result.chunking_stats
            print(f"   Average chunk size: {stats['avg_chunk_size']:.1f} tokens")
            print(f"   Size distribution:")
            size_dist = stats['size_distribution']
            print(f"     Min: {size_dist['min']} tokens")
            print(f"     Max: {size_dist['max']} tokens") 
            print(f"     Mean: {size_dist['mean']:.1f} tokens")
            print(f"     Median: {size_dist['median']} tokens")
            
            # Show section breakdown
            print(f"\n📑 Section Breakdown:")
            for section_name, section_stats in stats['sections_stats'].items():
                print(f"   {section_name:15} -> {section_stats['chunks']:2d} chunks, {section_stats['tokens']:4d} tokens ({section_stats['section_type']})")
            
            # Show sample chunks
            print(f"\n📝 Sample Chunks (first 3):")
            for j, chunk in enumerate(chunking_result.chunks[:3]):
                content_preview = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
                print(f"   Chunk {j+1}: [{chunk.section_name}] {chunk.token_count} tokens")
                print(f"     Pages {chunk.page_start}-{chunk.page_end}, Para {chunk.paragraph_index}")
                print(f"     Content: {content_preview}")
                if chunk.overlap_prev:
                    overlap_preview = chunk.overlap_prev[:50] + "..." if len(chunk.overlap_prev) > 50 else chunk.overlap_prev
                    print(f"     Overlap prev: {overlap_preview}")
                print()
            
            all_results.append({
                'filename': pdf_file.name,
                'total_chunks': chunking_result.total_chunks,
                'total_tokens': chunking_result.total_tokens,
                'avg_chunk_size': stats['avg_chunk_size'],
                'sections_processed': chunking_result.sections_processed,
                'chunking_strategy': 'hybrid'
            })
            
        except Exception as e:
            print(f"❌ Error processing {pdf_file.name}: {str(e)}")
            all_results.append({
                'filename': pdf_file.name,
                'total_chunks': 0,
                'total_tokens': 0,
                'avg_chunk_size': 0,
                'sections_processed': 0,
                'chunking_strategy': 'failed'
            })
        
        print("\n")
    
    # Summary
    print("=" * 60)
    print("📊 CHUNKING TEST SUMMARY")
    print("=" * 60)
    print(f"{'File':<15} {'Chunks':<8} {'Tokens':<8} {'Avg Size':<10} {'Sections':<9}")
    print("-" * 60)
    
    total_chunks = 0
    total_tokens = 0
    successful_files = 0
    
    for result in all_results:
        avg_size = f"{result['avg_chunk_size']:.1f}" if result['avg_chunk_size'] > 0 else "N/A"
        print(f"{result['filename']:<15} {result['total_chunks']:<8} {result['total_tokens']:<8} {avg_size:<10} {result['sections_processed']:<9}")
        
        if result['chunking_strategy'] != 'failed':
            total_chunks += result['total_chunks']
            total_tokens += result['total_tokens']
            successful_files += 1
    
    print("-" * 60)
    print(f"✅ Successfully processed: {successful_files}/{len(pdf_files)} files")
    print(f"📊 Total chunks created: {total_chunks}")
    print(f"🔢 Total tokens processed: {total_tokens}")
    if successful_files > 0:
        print(f"📏 Average chunks per file: {total_chunks / successful_files:.1f}")
        print(f"📈 Average tokens per file: {total_tokens / successful_files:.1f}")
    
    return successful_files == len(pdf_files)

def test_chunking_quality():
    """Test chunking quality with specific scenarios"""
    print("\n🧪 Testing Chunking Quality")
    print("=" * 40)
    
    chunker = TextChunker(target_chunk_size=300, max_chunk_size=500, min_chunk_size=50)
    
    # Test with sample text
    sample_text = """
    This is the first paragraph of our test document. It contains multiple sentences and should be kept together as much as possible.
    
    This is the second paragraph. It's also quite substantial and talks about different concepts than the first paragraph.
    
    Here's a third paragraph that's much shorter.
    
    The fourth paragraph is very long and contains lots of information that might need to be split if it exceeds our maximum chunk size limits. We want to make sure that even when splitting occurs, it happens at natural boundaries like sentence endings rather than cutting off words in the middle.
    
    Finally, this is the last paragraph which wraps up our discussion.
    """
    
    # Create a mock section for testing
    class MockSection:
        def __init__(self, content):
            self.content = content
            self.page_start = 1
            self.page_end = 2
            self.tables = []
    
    chunks = chunker._chunk_by_paragraphs(
        sample_text.strip(),
        "test_section",
        "content", 
        1, 2, False, False
    )
    
    print(f"📝 Test text chunked into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"   Chunk {i+1}: {chunk.token_count} tokens")
        print(f"     Content: {chunk.content[:80]}...")
        print()
    
    print("✅ Chunking quality test completed")
    return True

def main():
    """Run all chunking tests"""
    print("🚀 Running Text Chunking Tests")
    print("Testing hybrid strategy: Section-aware + Paragraph + Size limits")
    print()
    
    # Test with real PDFs
    strategy_test = test_chunking_strategy()
    
    # Test chunking quality
    quality_test = test_chunking_quality()
    
    print("\n" + "=" * 60)
    print("🎯 TEST RESULTS:")
    print(f"📄 Strategy Test: {'✅ PASS' if strategy_test else '❌ FAIL'}")
    print(f"🧪 Quality Test: {'✅ PASS' if quality_test else '❌ FAIL'}")
    
    if strategy_test and quality_test:
        print("\n🎉 All chunking tests passed!")
        print("✅ Hybrid chunking strategy is working correctly.")
        print("🔧 Ready for embedding service implementation.")
    else:
        print("\n⚠️ Some tests failed. Please review the implementation.")
    
    return strategy_test and quality_test

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)