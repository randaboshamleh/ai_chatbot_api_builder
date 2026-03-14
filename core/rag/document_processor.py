import hashlib
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader,
)
from langchain_core.documents import Document as LangchainDocument

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    معالج الوثائق: تحميل → تقطيع → تجهيز للـ Embedding
    """

    LOADER_MAPPING = {
        'application/pdf': PyPDFLoader,
        'application/msword': Docx2txtLoader,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': Docx2txtLoader,
       'application/vnd.ms-excel': None,
       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': None,
        'text/plain': TextLoader,
        'text/csv': CSVLoader,
    }

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        )

    def load_document(self, file_path: str, file_type: str) -> List[LangchainDocument]:
        """تحميل الوثيقة حسب نوعها"""
        loader_class = self.LOADER_MAPPING.get(file_type)
        
        if not loader_class:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        loader = loader_class(file_path)
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} pages from {file_path}")
        return documents

    def split_documents(
        self, 
        documents: List[LangchainDocument],
        metadata: Dict[str, Any] = None
    ) -> List[LangchainDocument]:
        """تقطيع الوثيقة إلى chunks مع إضافة metadata"""
        chunks = self.text_splitter.split_documents(documents)
       
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                'chunk_index': i,
                'total_chunks': len(chunks),
                **(metadata or {})
            })
        
        logger.info(f"Split into {len(chunks)} chunks")
        return chunks

    def process(
        self, 
        file_path: str, 
        file_type: str,
        metadata: Dict[str, Any] = None
    ) -> List[LangchainDocument]:
        """Pipeline كامل للمعالجة"""
        start_time = time.time()
        
        documents = self.load_document(file_path, file_type)
        chunks = self.split_documents(documents, metadata)
        
        processing_time = time.time() - start_time
        logger.info(f"Document processed in {processing_time:.2f}s")
        
        return chunks, processing_time

    @staticmethod
    def compute_checksum(file_path: str) -> str:
        """حساب checksum للتحقق من سلامة الملف"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()