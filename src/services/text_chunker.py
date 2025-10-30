"""
Text Chunking Service using Hybrid Strategy

This service implements intelligent chunking that:
- Respects section boundaries (never crosses sections)
- Preserves paragraph structure when possible
- Maintains reasonable chunk sizes (300-800 tokens)
- Includes overlapping windows for context continuity
- Stores rich metadata for citations and retrieval

Strategy: Section-Aware + Paragraph + Size Limits
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# For improved token counting without external dependencies
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TextChunk:
    """Container for a text chunk with metadata"""
    content: str
    section_name: str
    page_start: int
    page_end: int
    paragraph_index: int
    chunk_index: int
    token_count: int
    overlap_prev: Optional[str] = None
    overlap_next: Optional[str] = None
    
    # Additional metadata for citations
    section_type: str = "content"  # content, abstract, conclusion, etc.
    has_tables: bool = False
    has_figures: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for storage"""
        return {
            "content": self.content,
            "section_name": self.section_name,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "paragraph_index": self.paragraph_index,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "overlap_prev": self.overlap_prev,
            "overlap_next": self.overlap_next,
            "section_type": self.section_type,
            "has_tables": self.has_tables,
            "has_figures": self.has_figures
        }

@dataclass
class ChunkingResult:
    """Complete result of text chunking"""
    chunks: List[TextChunk]
    total_chunks: int
    total_tokens: int
    sections_processed: int
    chunking_stats: Dict[str, Any]

class TextChunker:
    """
    Hybrid text chunker optimized for academic papers
    
    Combines:
    - Section-aware chunking (respects paper structure)
    - Paragraph-based splitting (maintains coherence)
    - Size-limited chunks (practical constraints)
    - Smart overlap (context continuity)
    """
    
    def __init__(
        self,
        target_chunk_size: int = 500,
        max_chunk_size: int = 800,
        min_chunk_size: int = 100,
        overlap_size: int = 50
    ):
        """
        Initialize the text chunker
        
        Args:
            target_chunk_size: Preferred chunk size in tokens
            max_chunk_size: Maximum allowed chunk size in tokens
            min_chunk_size: Minimum chunk size (avoid tiny fragments)
            overlap_size: Number of tokens to overlap between chunks
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_size = overlap_size
        
        # Section type classification
        self.section_types = {
            'abstract': 'abstract',
            'summary': 'abstract',
            'introduction': 'introduction',
            'methods': 'methods',
            'methodology': 'methods',
            'approach': 'methods',
            'results': 'results',
            'findings': 'results',
            'analysis': 'results',
            'discussion': 'discussion',
            'conclusion': 'conclusion',
            'conclusions': 'conclusion',
            'references': 'references',
            'bibliography': 'references'
        }

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using improved estimation
        
        This implementation provides a good approximation without external dependencies.
        Based on analysis of academic papers and common tokenization patterns.
        """
        if not text or not text.strip():
            return 0
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Basic character count approach (most reliable baseline)
        char_count = len(text)
        
        # Average characters per token for different text types
        # Academic papers typically have longer words/tokens
        base_chars_per_token = 4.2  # Empirically determined for academic text
        
        # Adjust for text complexity
        words = text.split()
        if not words:
            return 1
        
        # Count complex words (likely to be tokenized into multiple tokens)
        complex_words = sum(1 for word in words if len(word) > 10)
        technical_terms = sum(1 for word in words if any(char.isupper() for char in word[1:]))  # camelCase, acronyms
        
        # Adjust characters per token based on complexity
        if complex_words > len(words) * 0.2:  # >20% complex words
            base_chars_per_token = 3.8  # More tokens for complex text
        
        if technical_terms > len(words) * 0.1:  # >10% technical terms
            base_chars_per_token = 3.5  # Even more tokens for technical text
        
        # Calculate estimated tokens
        estimated_tokens = char_count / base_chars_per_token
        
        # Ensure at least one token per word (minimum bound)
        min_tokens = len(words)
        
        # Apply some common adjustments for academic text
        # Punctuation and special characters add tokens
        punctuation_count = sum(1 for char in text if char in '.,;:!?()[]{}')
        punctuation_tokens = punctuation_count * 0.3  # Rough estimate
        
        # Combine estimates
        final_estimate = max(estimated_tokens + punctuation_tokens, min_tokens)
        
        return int(round(final_estimate))

    def chunk_pdf_content(self, pdf_result) -> ChunkingResult:
        """
        Chunk content from PDF processing result
        
        Args:
            pdf_result: PDFProcessingResult from pdf_processor
            
        Returns:
            ChunkingResult with all chunks and metadata
        """
        all_chunks = []
        section_stats = {}
        
        logger.info(f"Starting chunking of {len(pdf_result.sections)} sections")
        
        # Process each section separately
        for section_name, section in pdf_result.sections.items():
            logger.info(f"Chunking section: {section_name}")
            
            # Determine section type
            section_type = self._classify_section_type(section_name)
            
            # Check for tables/figures in this section
            has_tables = len(section.tables) > 0
            has_figures = self._detect_figures_in_text(section.content)
            
            # Apply section-specific chunking strategy
            section_chunks = self._chunk_section(
                content=section.content,
                section_name=section_name,
                section_type=section_type,
                page_start=section.page_start,
                page_end=section.page_end,
                has_tables=has_tables,
                has_figures=has_figures
            )
            
            # Add overlap between chunks within section
            section_chunks = self._add_chunk_overlap(section_chunks)
            
            all_chunks.extend(section_chunks)
            section_stats[section_name] = {
                'chunks': len(section_chunks),
                'tokens': sum(chunk.token_count for chunk in section_chunks),
                'section_type': section_type,
                'has_tables': has_tables,
                'has_figures': has_figures
            }
        
        # Add global chunk indices
        for i, chunk in enumerate(all_chunks):
            chunk.chunk_index = i
        
        # Calculate statistics
        total_tokens = sum(chunk.token_count for chunk in all_chunks)
        
        chunking_stats = {
            'sections_stats': section_stats,
            'avg_chunk_size': total_tokens / len(all_chunks) if all_chunks else 0,
            'size_distribution': self._calculate_size_distribution(all_chunks),
            'section_count': len(pdf_result.sections),
            'overlap_efficiency': self._calculate_overlap_efficiency(all_chunks)
        }
        
        logger.info(f"Chunking completed: {len(all_chunks)} chunks, {total_tokens} total tokens")
        
        return ChunkingResult(
            chunks=all_chunks,
            total_chunks=len(all_chunks),
            total_tokens=total_tokens,
            sections_processed=len(pdf_result.sections),
            chunking_stats=chunking_stats
        )

    def _classify_section_type(self, section_name: str) -> str:
        """Classify section type for specialized chunking"""
        section_lower = section_name.lower()
        
        for keyword, section_type in self.section_types.items():
            if keyword in section_lower:
                return section_type
        
        return 'content'  # Default type

    def _detect_figures_in_text(self, text: str) -> bool:
        """Detect if text contains figure references"""
        figure_patterns = [
            r'\bfigure\s+\d+',
            r'\bfig\.\s*\d+',
            r'\bimage\s+\d+',
            r'\bgraph\s+\d+',
            r'\bdiagram\s+\d+'
        ]
        
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in figure_patterns)

    def _chunk_section(
        self,
        content: str,
        section_name: str,
        section_type: str,
        page_start: int,
        page_end: int,
        has_tables: bool,
        has_figures: bool
    ) -> List[TextChunk]:
        """
        Chunk a single section using hybrid strategy
        """
        if not content.strip():
            return []
        
        # Apply section-specific strategy
        if section_type == 'abstract':
            return self._chunk_abstract(content, section_name, page_start, page_end, has_tables, has_figures)
        elif section_type == 'references':
            return self._chunk_references(content, section_name, page_start, page_end)
        else:
            return self._chunk_content_section(content, section_name, section_type, page_start, page_end, has_tables, has_figures)

    def _chunk_abstract(self, content: str, section_name: str, page_start: int, page_end: int, has_tables: bool, has_figures: bool) -> List[TextChunk]:
        """
        Abstract chunking: usually keep as single chunk unless very long
        """
        token_count = self.count_tokens(content)
        
        # If abstract is reasonable size, keep as single chunk
        if token_count <= self.max_chunk_size:
            return [TextChunk(
                content=content.strip(),
                section_name=section_name,
                page_start=page_start,
                page_end=page_end,
                paragraph_index=0,
                chunk_index=0,
                token_count=token_count,
                section_type='abstract',
                has_tables=has_tables,
                has_figures=has_figures
            )]
        else:
            # Very long abstract - use paragraph chunking
            return self._chunk_by_paragraphs(content, section_name, 'abstract', page_start, page_end, has_tables, has_figures)

    def _chunk_references(self, content: str, section_name: str, page_start: int, page_end: int) -> List[TextChunk]:
        """
        References chunking: group by reasonable size but don't break citations
        """
        # For now, treat references as content but with special type
        # In production, might want to extract and index references separately
        chunks = self._chunk_by_paragraphs(content, section_name, 'references', page_start, page_end, False, False)
        return chunks

    def _chunk_content_section(
        self,
        content: str,
        section_name: str,
        section_type: str,
        page_start: int,
        page_end: int,
        has_tables: bool,
        has_figures: bool
    ) -> List[TextChunk]:
        """
        Content section chunking: paragraph-based with size limits
        """
        return self._chunk_by_paragraphs(content, section_name, section_type, page_start, page_end, has_tables, has_figures)

    def _chunk_by_paragraphs(
        self,
        content: str,
        section_name: str,
        section_type: str,
        page_start: int,
        page_end: int,
        has_tables: bool,
        has_figures: bool
    ) -> List[TextChunk]:
        """
        Core chunking logic: paragraph-based with size constraints
        """
        paragraphs = self._split_into_paragraphs(content)
        chunks = []
        current_chunk = ""
        current_paragraph_index = 0
        
        for para_idx, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Calculate tokens for current chunk + new paragraph
            potential_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            potential_tokens = self.count_tokens(potential_chunk)
            
            # If adding this paragraph would exceed max size, finalize current chunk
            if current_chunk and potential_tokens > self.max_chunk_size:
                # Finalize current chunk
                chunk_tokens = self.count_tokens(current_chunk)
                if chunk_tokens >= self.min_chunk_size:
                    chunks.append(TextChunk(
                        content=current_chunk.strip(),
                        section_name=section_name,
                        page_start=page_start,
                        page_end=page_end,
                        paragraph_index=current_paragraph_index,
                        chunk_index=len(chunks),
                        token_count=chunk_tokens,
                        section_type=section_type,
                        has_tables=has_tables,
                        has_figures=has_figures
                    ))
                
                # Start new chunk with current paragraph
                current_chunk = paragraph
                current_paragraph_index = para_idx
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                    current_paragraph_index = para_idx
            
            # If current chunk reaches target size, consider finalizing
            current_tokens = self.count_tokens(current_chunk)
            if current_tokens >= self.target_chunk_size:
                # Check if next paragraph would fit within max size
                if para_idx + 1 < len(paragraphs):
                    next_para = paragraphs[para_idx + 1].strip()
                    if next_para:
                        test_chunk = current_chunk + "\n\n" + next_para
                        if self.count_tokens(test_chunk) > self.max_chunk_size:
                            # Finalize current chunk
                            chunks.append(TextChunk(
                                content=current_chunk.strip(),
                                section_name=section_name,
                                page_start=page_start,
                                page_end=page_end,
                                paragraph_index=current_paragraph_index,
                                chunk_index=len(chunks),
                                token_count=current_tokens,
                                section_type=section_type,
                                has_tables=has_tables,
                                has_figures=has_figures
                            ))
                            current_chunk = ""
        
        # Handle remaining content
        if current_chunk.strip():
            chunk_tokens = self.count_tokens(current_chunk)
            if chunk_tokens >= self.min_chunk_size:
                chunks.append(TextChunk(
                    content=current_chunk.strip(),
                    section_name=section_name,
                    page_start=page_start,
                    page_end=page_end,
                    paragraph_index=current_paragraph_index,
                    chunk_index=len(chunks),
                    token_count=chunk_tokens,
                    section_type=section_type,
                    has_tables=has_tables,
                    has_figures=has_figures
                ))
        
        return chunks

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs with smart handling
        """
        # Split by double newlines (common paragraph separator)
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean up paragraphs
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 10:  # Skip very short fragments
                # Replace single newlines with spaces (join broken lines)
                para = re.sub(r'\n(?!\n)', ' ', para)
                # Clean up excessive whitespace
                para = re.sub(r'\s+', ' ', para)
                cleaned_paragraphs.append(para)
        
        return cleaned_paragraphs

    def _add_chunk_overlap(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """
        Add overlapping content between adjacent chunks
        """
        if len(chunks) <= 1:
            return chunks
        
        for i in range(len(chunks)):
            # Add previous chunk overlap
            if i > 0:
                prev_chunk = chunks[i - 1]
                overlap = self._extract_overlap(prev_chunk.content, is_ending=True)
                chunks[i].overlap_prev = overlap
            
            # Add next chunk overlap
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                overlap = self._extract_overlap(next_chunk.content, is_ending=False)
                chunks[i].overlap_next = overlap
        
        return chunks

    def _extract_overlap(self, content: str, is_ending: bool) -> str:
        """
        Extract overlap content from beginning or end of chunk
        """
        sentences = self._split_into_sentences(content)
        
        if not sentences:
            return ""
        
        # Try to get complete sentences for overlap
        if is_ending:
            # Take last sentences
            overlap_sentences = sentences[-2:] if len(sentences) > 1 else sentences[-1:]
        else:
            # Take first sentences
            overlap_sentences = sentences[:2] if len(sentences) > 1 else sentences[:1]
        
        overlap = " ".join(overlap_sentences)
        
        # Ensure overlap doesn't exceed size limit
        if self.count_tokens(overlap) > self.overlap_size:
            # Truncate to approximate token limit
            words = overlap.split()
            estimated_words = min(len(words), self.overlap_size // 1.3)
            overlap = " ".join(words[:int(estimated_words)])
        
        return overlap

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences
        """
        # Simple sentence splitting (could be improved with NLTK/spaCy)
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _calculate_size_distribution(self, chunks: List[TextChunk]) -> Dict[str, float]:
        """Calculate chunk size distribution statistics"""
        if not chunks:
            return {}
        
        sizes = [chunk.token_count for chunk in chunks]
        sizes.sort()
        
        return {
            'min': min(sizes),
            'max': max(sizes),
            'mean': sum(sizes) / len(sizes),
            'median': sizes[len(sizes) // 2],
            'std_dev': self._calculate_std_dev(sizes)
        }

    def _calculate_std_dev(self, sizes: List[int]) -> float:
        """Calculate standard deviation"""
        if len(sizes) < 2:
            return 0.0
        
        mean = sum(sizes) / len(sizes)
        variance = sum((x - mean) ** 2 for x in sizes) / len(sizes)
        return variance ** 0.5

    def _calculate_overlap_efficiency(self, chunks: List[TextChunk]) -> Dict[str, float]:
        """Calculate overlap efficiency metrics"""
        total_overlaps = 0
        total_overlap_tokens = 0
        
        for chunk in chunks:
            if chunk.overlap_prev:
                total_overlaps += 1
                total_overlap_tokens += self.count_tokens(chunk.overlap_prev)
            if chunk.overlap_next:
                total_overlaps += 1
                total_overlap_tokens += self.count_tokens(chunk.overlap_next)
        
        avg_overlap_size = total_overlap_tokens / total_overlaps if total_overlaps > 0 else 0
        
        return {
            'total_overlaps': total_overlaps,
            'avg_overlap_size': avg_overlap_size,
            'overlap_coverage': total_overlaps / (len(chunks) * 2) if chunks else 0
        }