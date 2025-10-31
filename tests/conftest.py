"""
Pytest configuration and fixtures for research paper RAG tests
"""
import pytest
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(scope="session")
def src_path():
    """Add src directory to Python path"""
    current_dir = Path(__file__).parent
    src_dir = current_dir.parent / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    return str(src_dir)

@pytest.fixture
def sample_papers_dir():
    """Path to sample papers directory"""
    return Path(__file__).parent.parent / "sample_papers"

@pytest.fixture
def embedding_service():
    """Initialize embedding service for tests"""
    from src.services.embedding_service import EmbeddingService
    return EmbeddingService(model_name="all-MiniLM-L6-v2", batch_size=8)

@pytest.fixture
def text_chunker():
    """Initialize text chunker for tests"""
    from src.services.text_chunker import TextChunker
    return TextChunker(target_chunk_size=300, max_chunk_size=500)

@pytest.fixture
def pdf_processor():
    """Initialize PDF processor for tests"""
    from src.services.pdf_processor import PDFProcessor
    return PDFProcessor()

@pytest.fixture
def qdrant_client():
    """Initialize Qdrant client for tests"""
    from src.services.qdrant_client import QdrantClientService
    return QdrantClientService(
        collection_name="test_collection",
        embedding_dim=384
    )

@pytest.fixture
def mock_pdf_result():
    """Create mock PDF result for testing"""
    class MockSection:
        def __init__(self, name, content, page_start, page_end):
            self.content = content
            self.page_start = page_start
            self.page_end = page_end
            self.tables = []
    
    class MockMetadata:
        def __init__(self):
            self.title = "Mock Research Paper on Machine Learning"
            self.authors = "John Doe, Jane Smith"
            self.year = 2024
            self.num_pages = 10
            self.file_size = 1024000
    
    class MockPDFResult:
        def __init__(self):
            self.metadata = MockMetadata()
            self.sections = {
                'abstract': MockSection(
                    'abstract',
                    'This paper presents a comprehensive analysis of machine learning techniques for text classification. Our approach combines traditional feature engineering with modern deep learning methods to achieve state-of-the-art performance.',
                    1, 1
                ),
                'introduction': MockSection(
                    'introduction', 
                    'Text classification is a fundamental task in natural language processing. It involves categorizing text documents into predefined categories based on their content. Traditional approaches rely on handcrafted features, while modern methods use neural networks. Recent advances in transformer architectures have shown remarkable improvements in various NLP tasks.',
                    1, 2
                ),
                'methods': MockSection(
                    'methods',
                    'Our methodology involves a hybrid approach combining convolutional neural networks with attention mechanisms. We utilize a multi-layer architecture with dropout regularization and batch normalization. The model is trained using the Adam optimizer with a learning rate of 0.001.',
                    2, 4
                )
            }
    
    return MockPDFResult()

# Configure pytest for async tests
pytest_plugins = ['pytest_asyncio']