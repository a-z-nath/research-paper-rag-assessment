#!/usr/bin/env python3
"""
Test script to extract metadata only from sample PDF files
No database operations - just metadata extraction
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.pdf_processor import PDFProcessor

def test_pdf_metadata_extraction():
    """Test metadata extraction from all sample PDFs"""
    print("📚 Testing PDF Metadata Extraction from Sample Papers")
    print("=" * 60)
    
    # Initialize PDF processor
    processor = PDFProcessor()
    
    # Get all PDF files from sample_papers directory
    sample_dir = Path("sample_papers")
    if not sample_dir.exists():
        print("❌ sample_papers directory not found!")
        return False
    
    pdf_files = sorted(list(sample_dir.glob("*.pdf")))
    if not pdf_files:
        print("❌ No PDF files found in sample_papers directory!")
        return False
    
    print(f"Found {len(pdf_files)} PDF files to process\n")
    
    # Process each PDF file
    results = []
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"📄 Processing {i}/{len(pdf_files)}: {pdf_file.name}")
        print("-" * 40)
        
        try:
            # Process PDF and extract metadata
            result = processor.process_pdf(str(pdf_file))
            metadata = result.metadata
            
            # Display metadata
            print(f"📁 Filename: {pdf_file.name}")
            print(f"📖 Title: {metadata.title or 'Not detected'}")
            print(f"👥 Authors: {metadata.authors or 'Not detected'}")
            print(f"📅 Year: {metadata.year or 'Not detected'}")
            print(f"📊 Pages: {metadata.num_pages}")
            print(f"💾 File Size: {metadata.file_size:,} bytes ({metadata.file_size / 1024 / 1024:.2f} MB)")
            
            # Store results for summary
            results.append({
                'filename': pdf_file.name,
                'title': metadata.title,
                'authors': metadata.authors,
                'year': metadata.year,
                'pages': metadata.num_pages,
                'size_mb': metadata.file_size / 1024 / 1024,
                'processing_errors': len(result.processing_errors),
                'sections_found': len(result.sections),
                'tables_found': len(result.tables)
            })
            
            if result.processing_errors:
                print(f"⚠️ Processing errors: {len(result.processing_errors)}")
                for error in result.processing_errors:
                    print(f"   - {error}")
            
            print(f"📑 Additional info: {len(result.sections)} sections, {len(result.tables)} tables found")
            print()
            
        except Exception as e:
            print(f"❌ Error processing {pdf_file.name}: {str(e)}")
            results.append({
                'filename': pdf_file.name,
                'title': 'ERROR',
                'authors': 'ERROR',
                'year': 'ERROR',
                'pages': 0,
                'size_mb': 0,
                'processing_errors': 1,
                'sections_found': 0,
                'tables_found': 0
            })
            print()
    
    # Summary table
    print("=" * 60)
    print("📊 METADATA EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"{'Filename':<15} {'Title':<30} {'Authors':<25} {'Year':<6} {'Pages':<6}")
    print("-" * 82)
    
    for result in results:
        title = result['title'][:27] + "..." if result['title'] and len(result['title']) > 30 else (result['title'] or 'N/A')
        authors = result['authors'][:22] + "..." if result['authors'] and len(result['authors']) > 25 else (result['authors'] or 'N/A')
        year = str(result['year']) if result['year'] else 'N/A'
        
        print(f"{result['filename']:<15} {title:<30} {authors:<25} {year:<6} {result['pages']:<6}")
    
    # Statistics
    successful = len([r for r in results if r['processing_errors'] == 0])
    total_pages = sum(r['pages'] for r in results)
    total_size = sum(r['size_mb'] for r in results)
    titles_found = len([r for r in results if r['title'] and r['title'] != 'ERROR'])
    authors_found = len([r for r in results if r['authors'] and r['authors'] != 'ERROR'])
    years_found = len([r for r in results if r['year'] and r['year'] != 'ERROR'])
    
    print("-" * 82)
    print(f"✅ Successfully processed: {successful}/{len(results)} files")
    print(f"📊 Total pages processed: {total_pages}")
    print(f"💾 Total size processed: {total_size:.2f} MB")
    print(f"📖 Titles extracted: {titles_found}/{len(results)}")
    print(f"👥 Authors extracted: {authors_found}/{len(results)}")
    print(f"📅 Years extracted: {years_found}/{len(results)}")
    
    return successful == len(results)

def main():
    """Run metadata extraction test"""
    print("🔬 PDF Metadata Extraction Test")
    print("Testing PDF processor with sample papers - metadata only")
    print()
    
    success = test_pdf_metadata_extraction()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All PDF files processed successfully!")
        print("✅ Metadata extraction is working correctly.")
    else:
        print("⚠️ Some files had processing errors.")
        print("💡 Check the details above for specific issues.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)