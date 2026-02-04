"""
PDF Processing Service using PyMuPDF and pdfplumber for table extraction

This service handles:
- Text extraction from PDF files
- Section-aware processing (Abstract, Introduction, Methods, Results, Conclusion)
- Metadata extraction (title, authors, year, page count)
- Table extraction using pdfplumber
- Error handling and fallback mechanisms
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import fitz  # PyMuPDF
import pdfplumber

logger = logging.getLogger(__name__)

@dataclass
class PDFMetadata:
    """Container for PDF metadata"""
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    num_pages: int = 0
    file_size: int = 0

@dataclass
class PDFSection:
    """Container for PDF section content"""
    name: str
    content: str
    page_start: int
    page_end: int
    tables: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.tables is None:
            self.tables = []

@dataclass
class PDFProcessingResult:
    """Complete result of PDF processing"""
    metadata: PDFMetadata
    sections: Dict[str, PDFSection]
    full_text: str
    page_texts: List[str]
    tables: List[Dict[str, Any]]
    processing_errors: List[str]

class PDFProcessor:
    """
    Advanced PDF processor using PyMuPDF for text and pdfplumber for tables
    """
    
    # Common section headers to identify
    SECTION_PATTERNS = {
        'abstract': [
            r'\babstract\b',
            r'\bsummary\b',
            r'\bexecutive summary\b'
        ],
        'introduction': [
            r'\bintroduction\b',
            r'\b1\.\s*introduction\b',
            r'\b1\s+introduction\b'
        ],
        'methods': [
            r'\bmethods?\b',
            r'\bmethodology\b',
            r'\bapproach\b',
            r'\bmaterials? and methods?\b',
            r'\bexperimental (setup|design|procedure)\b'
        ],
        'results': [
            r'\bresults?\b',
            r'\bfindings?\b',
            r'\bexperiment(al)? results?\b',
            r'\banalysis\b'
        ],
        'discussion': [
            r'\bdiscussion\b',
            r'\bresults? and discussion\b'
        ],
        'conclusion': [
            r'\bconclusions?\b',
            r'\bsummary and conclusions?\b',
            r'\bfuture work\b'
        ],
        'references': [
            r'\breferences?\b',
            r'\bbibliography\b',
            r'\bcitations?\b'
        ]
    }

    def __init__(self):
        """Initialize the PDF processor"""
        self.reset()

    def reset(self):
        """Reset processor state"""
        self.current_file = None
        self.doc = None
        self.pdf_plumber = None

    def process_pdf(self, file_path: str) -> PDFProcessingResult:
        """
        Process a PDF file and extract all relevant information
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            PDFProcessingResult containing all extracted information
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        if not file_path.suffix.lower() == '.pdf':
            raise ValueError(f"File is not a PDF: {file_path}")

        self.current_file = file_path
        processing_errors = []

        try:
            # Open PDF with PyMuPDF
            self.doc = fitz.open(str(file_path))
            
            # Extract basic metadata
            metadata = self._extract_metadata()
            
            # Extract text from all pages
            page_texts = self._extract_page_texts()
            full_text = '\n\n'.join(page_texts)
            
            # Identify and extract sections
            sections = self._extract_sections(page_texts)
            
            # Extract tables using pdfplumber
            tables = self._extract_tables()
            
            # Associate tables with sections
            self._associate_tables_with_sections(sections, tables)
            
            return PDFProcessingResult(
                metadata=metadata,
                sections=sections,
                full_text=full_text,
                page_texts=page_texts,
                tables=tables,
                processing_errors=processing_errors
            )
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            processing_errors.append(f"Processing error: {str(e)}")
            
            # Return minimal result with error
            return PDFProcessingResult(
                metadata=PDFMetadata(num_pages=0),
                sections={},
                full_text="",
                page_texts=[],
                tables=[],
                processing_errors=processing_errors
            )
        finally:
            self._cleanup()

    def _extract_metadata(self) -> PDFMetadata:
        """Extract metadata from PDF document"""
        try:
            # Get basic metadata from PyMuPDF
            doc_metadata = self.doc.metadata
            
            # Extract title (from metadata or first page)
            title = self._extract_title(doc_metadata)
            
            # Extract authors
            authors = self._extract_authors(doc_metadata)
            
            # Extract year
            year = self._extract_year(doc_metadata)
            
            # Get file info
            num_pages = len(self.doc)
            file_size = self.current_file.stat().st_size
            
            return PDFMetadata(
                title=title,
                authors=authors,
                year=year,
                num_pages=num_pages,
                file_size=file_size
            )
            
        except Exception as e:
            logger.warning(f"Error extracting metadata: {str(e)}")
            return PDFMetadata(num_pages=len(self.doc) if self.doc else 0)

    def _extract_title(self, doc_metadata: Dict) -> Optional[str]:
        """Extract title from metadata or first page"""
        # Try metadata first
        if doc_metadata.get('title'):
            title = doc_metadata['title'].strip()
            if len(title) > 10:  # Reasonable title length
                return title
        
        # Try to extract from first page
        if len(self.doc) > 0:
            first_page = self.doc[0]
            text = first_page.get_text()
            
            # Look for title patterns in first few lines
            lines = text.split('\n')[:10]
            for line in lines:
                line = line.strip()
                # Skip short lines, page numbers, headers
                if (len(line) > 20 and 
                    not re.match(r'^\d+$', line) and
                    not line.lower().startswith(('page', 'abstract', 'introduction'))):
                    return line
        
        return None

    def _extract_authors(self, doc_metadata: Dict) -> Optional[str]:
        """Extract authors from metadata or first page"""
        # Try metadata first
        if doc_metadata.get('author'):
            return doc_metadata['author'].strip()
        
        # Try to extract from first page
        if len(self.doc) > 0:
            first_page = self.doc[0]
            text = first_page.get_text()
            
            # Look for author patterns
            author_patterns = [
                r'([A-Z][a-z]+ [A-Z][a-z]+(?:,?\s+[A-Z][a-z]+ [A-Z][a-z]+)*)',
                r'Authors?:\s*([^\n]+)',
                r'By:?\s*([^\n]+)'
            ]
            
            for pattern in author_patterns:
                match = re.search(pattern, text, re.MULTILINE)
                if match:
                    return match.group(1).strip()
        
        return None

    def _extract_year(self, doc_metadata: Dict) -> Optional[int]:
        """Extract publication year"""
        # Try metadata creation date
        if doc_metadata.get('creationDate'):
            try:
                # PyMuPDF date format: D:YYYYMMDDHHmmSSOHH'mm'
                date_str = doc_metadata['creationDate']
                if date_str.startswith('D:') and len(date_str) >= 6:
                    year_str = date_str[2:6]
                    year = int(year_str)
                    if 1900 <= year <= 2030:
                        return year
            except (ValueError, IndexError):
                pass
        
        # Try to find year in first page text
        if len(self.doc) > 0:
            first_page = self.doc[0]
            text = first_page.get_text()
            
            # Look for 4-digit years
            year_matches = re.findall(r'\b(19\d{2}|20[0-3]\d)\b', text)
            if year_matches:
                # Return the most recent reasonable year
                years = [int(y) for y in year_matches]
                years = [y for y in years if 1900 <= y <= 2030]
                if years:
                    return max(years)
        
        return None

    def _extract_page_texts(self) -> List[str]:
        """Extract text from all pages"""
        page_texts = []
        
        for page_num in range(len(self.doc)):
            try:
                page = self.doc[page_num]
                text = page.get_text()
                
                # Clean up the text
                text = self._clean_text(text)
                page_texts.append(text)
                
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                page_texts.append("")
        
        return page_texts

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers (simple heuristic)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip very short lines, isolated numbers, common headers/footers
            if (len(line) > 3 and 
                not re.match(r'^\d+$', line) and
                not re.match(r'^Page \d+', line, re.IGNORECASE)):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()

    def _extract_sections(self, page_texts: List[str]) -> Dict[str, PDFSection]:
        """Identify and extract sections from the document"""
        full_text = '\n\n'.join(page_texts)
        sections = {}
        
        # Find section boundaries
        section_boundaries = self._find_section_boundaries(full_text, page_texts)
        
        # Extract content for each identified section
        for section_name, (start_pos, end_pos, start_page, end_page) in section_boundaries.items():
            content = full_text[start_pos:end_pos].strip()
            
            sections[section_name] = PDFSection(
                name=section_name,
                content=content,
                page_start=start_page,
                page_end=end_page
            )
        
        return sections

    def _find_section_boundaries(self, full_text: str, page_texts: List[str]) -> Dict[str, Tuple[int, int, int, int]]:
        """Find start and end positions of sections"""
        boundaries = {}
        text_lower = full_text.lower()
        
        # Find matches for each section type
        section_matches = {}
        for section_name, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, text_lower, re.MULTILINE | re.IGNORECASE))
                if matches:
                    # Take the first match for this section
                    section_matches[section_name] = matches[0]
                    break
        
        # Sort sections by their position in the document
        sorted_sections = sorted(section_matches.items(), key=lambda x: x[1].start())
        
        # Determine boundaries
        for i, (section_name, match) in enumerate(sorted_sections):
            start_pos = match.start()
            
            # End position is the start of the next section or end of document
            if i + 1 < len(sorted_sections):
                end_pos = sorted_sections[i + 1][1].start()
            else:
                end_pos = len(full_text)
            
            # Find page numbers for this section
            start_page = self._find_page_for_position(start_pos, page_texts)
            end_page = self._find_page_for_position(end_pos, page_texts)
            
            boundaries[section_name] = (start_pos, end_pos, start_page, end_page)
        
        return boundaries

    def _find_page_for_position(self, position: int, page_texts: List[str]) -> int:
        """Find which page contains the given text position"""
        current_pos = 0
        
        for page_num, page_text in enumerate(page_texts):
            if current_pos <= position < current_pos + len(page_text):
                return page_num + 1  # 1-indexed page numbers
            current_pos += len(page_text) + 2  # +2 for '\n\n' separator
        
        return len(page_texts)  # Last page if position is beyond text

    def _extract_tables(self) -> List[Dict[str, Any]]:
        """Extract tables using pdfplumber"""
        tables = []
        
        try:
            with pdfplumber.open(str(self.current_file)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Extract tables from this page
                        page_tables = page.extract_tables()
                        
                        for table_idx, table_data in enumerate(page_tables):
                            if table_data and len(table_data) > 1:  # Skip empty or single-row tables
                                table_info = {
                                    'page': page_num + 1,
                                    'table_index': table_idx,
                                    'data': table_data,
                                    'headers': table_data[0] if table_data else [],
                                    'rows': table_data[1:] if len(table_data) > 1 else [],
                                    'num_rows': len(table_data) - 1,
                                    'num_cols': len(table_data[0]) if table_data else 0
                                }
                                tables.append(table_info)
                                
                    except Exception as e:
                        logger.warning(f"Error extracting tables from page {page_num + 1}: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.warning(f"Error opening PDF with pdfplumber: {str(e)}")
        
        return tables

    def _associate_tables_with_sections(self, sections: Dict[str, PDFSection], tables: List[Dict[str, Any]]):
        """Associate extracted tables with their respective sections"""
        for table in tables:
            table_page = table['page']
            
            # Find which section this table belongs to
            for section_name, section in sections.items():
                if section.page_start <= table_page <= section.page_end:
                    section.tables.append(table)
                    break

    def _cleanup(self):
        """Clean up resources"""
        if self.doc:
            self.doc.close()
            self.doc = None
        
        if self.pdf_plumber:
            self.pdf_plumber = None
        
        self.current_file = None

    def __del__(self):
        """Ensure resources are cleaned up"""
        self._cleanup()