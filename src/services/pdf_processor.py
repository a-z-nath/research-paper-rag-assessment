"""
PDF processing service with metadata extraction and intelligent chunking
"""
import re
from typing import List, Dict, Tuple
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import os


class PDFProcessor:
    """Handle PDF extraction, metadata parsing, and chunking"""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 200):
        """
        Initialize PDF processor with optimized chunking parameters
        
        Larger chunks (800 chars) provide more context per chunk
        Higher overlap (200 chars) preserves context across boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # Hierarchical separators - tries paragraph, then sentence, then word
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            length_function=len,
            keep_separator=True,  # Keep separators for better context
        )
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, any]:
        """
        Extract metadata from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with title, authors, year, total_pages
        """
        try:
            reader = PdfReader(pdf_path)
            metadata = reader.metadata
            
            # Extract from PDF metadata
            title = metadata.get('/Title', '') if metadata else ''
            authors = metadata.get('/Author', '') if metadata else ''
            
            # Try to extract from first page if metadata is empty
            if not title or not authors:
                first_page_text = reader.pages[0].extract_text()
                extracted = self._extract_from_text(first_page_text)
                if not title:
                    title = extracted.get('title', os.path.basename(pdf_path))
                if not authors:
                    authors = extracted.get('authors', 'Unknown')
            
            return {
                'title': title.strip() or os.path.basename(pdf_path),
                'authors': authors.strip() or 'Unknown',
                'year': self._extract_year(reader.pages[0].extract_text() if len(reader.pages) > 0 else ''),
                'total_pages': len(reader.pages)
            }
            
        except Exception as e:
            print(f"Error extracting metadata: {str(e)}")
            return {
                'title': os.path.basename(pdf_path),
                'authors': 'Unknown',
                'year': None,
                'total_pages': 0
            }
    
    def _extract_from_text(self, text: str) -> Dict[str, str]:
        """Extract title and authors from first page text"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        result = {'title': '', 'authors': ''}
        
        # Title is usually in first few lines (bold/large text)
        if len(lines) > 0:
            result['title'] = lines[0][:200]  # First line, max 200 chars
        
        # Look for author patterns
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            # Common patterns: names with commas, "by", email addresses nearby
            if re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', line) and len(line) < 100:
                if '@' not in line and 'abstract' not in line.lower():
                    result['authors'] = line
                    break
        
        return result
    
    def _extract_year(self, text: str) -> int:
        """Extract publication year from text"""
        # Look for 4-digit year between 1900-2030
        years = re.findall(r'\b(19|20)\d{2}\b', text[:500])
        if years:
            return int(years[0])
        return None
    
    def _detect_section(self, text: str) -> str:
        """
        Detect which section of the paper this text belongs to
        
        Helps organize chunks by academic paper structure for better context
        when answering queries (e.g., "What was the methodology?")
        """
        text_lower = text.lower()[:100]  # Check first 100 chars for section headers
        
        # Common section names in academic papers
        sections = {
            'Abstract': ['abstract'],
            'Introduction': ['introduction', '1. introduction', 'i. introduction'],
            'Related Work': ['related work', 'literature review', 'background'],
            'Methodology': ['methodology', 'methods', 'approach', 'method'],
            'Results': ['results', 'experiments', 'evaluation', 'findings'],
            'Discussion': ['discussion', 'analysis'],
            'Conclusion': ['conclusion', 'conclusions', 'summary'],
            'References': ['references', 'bibliography']
        }
        
        for section, keywords in sections.items():
            if any(keyword in text_lower for keyword in keywords):
                return section
        
        return 'Other'
    
    def process_pdf(self, pdf_path: str, start_page: int = 1, end_page: int = None) -> Tuple[List[Document], Dict]:
        """
        Process PDF: extract text, create chunks, add metadata
        
        This is the main processing pipeline:
        1. Extract metadata (title, authors, year)
        2. Extract text from each page
        3. Clean and normalize text
        4. Detect section for each page
        5. Split into semantic chunks using RecursiveCharacterTextSplitter
        6. Add metadata to each chunk for citation tracking
        
        Args:
            pdf_path: Path to PDF file
            start_page: Starting page (1-indexed, default: 1)
            end_page: Ending page (inclusive, default: all pages)
            
        Returns:
            Tuple of (chunks as Document objects, metadata dict)
        """
        print(f"📄 [PDF] Processing PDF: {os.path.basename(pdf_path)}")
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            print(f"   Total pages: {total_pages}")
            
            # Validate page range
            if start_page < 1:
                start_page = 1
            if end_page is None or end_page > total_pages:
                end_page = total_pages
            if start_page > end_page:
                return [], {}
            
            # Extract metadata (title, authors, year, page count)
            metadata = self.extract_metadata(pdf_path)
            
            # Extract text from pages
            documents = []
            for page_num in range(start_page - 1, end_page):
                page = reader.pages[page_num]
                content = page.extract_text()
                
                if content and content.strip():
                    # Clean text: remove excessive newlines and normalize whitespace
                    content = content.replace('\n\n\n', '\n\n')
                    content = ' '.join(content.split())
                    
                    # Detect which section this page belongs to (Introduction, Methods, etc.)
                    section = self._detect_section(content)
                    
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": pdf_path,
                            "page": page_num + 1,
                            "section": section,
                            "title": metadata['title'],
                            "authors": metadata['authors']
                        }
                    )
                    documents.append(doc)
            
            # Create chunks using RecursiveCharacterTextSplitter
            # This splits on natural boundaries (\n\n, \n, ., etc.) to maintain semantic coherence
            print(f"   Splitting into chunks (size={self.chunk_size}, overlap={self.chunk_overlap})...")
            chunks = self.text_splitter.split_documents(documents)
            print(f"   ✅ Created {len(chunks)} chunks")
            
            # Add chunk index to metadata for tracking
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk_index'] = i
            
            return chunks, metadata
            
        except Exception as e:
            print(f"❌ [PDF] Error processing PDF: {str(e)}")
            return [], {}
