"""PDF ingestion and document processing service."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from medicare_agent.config import settings
import logging

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting Medicare PDF documents and creating structured chunks."""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """Initialize ingestion service.

        Args:
            chunk_size: Size of text chunks (default from settings)
            chunk_overlap: Overlap between chunks (default from settings)
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

    def extract_pdf_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract content from PDF with page metadata.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of page dictionaries with text and metadata
        """
        logger.info(f"Extracting content from {pdf_path}")

        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        pages = []
        doc = fitz.open(pdf_path)

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")

                # Extract tables if present
                tables = self._extract_tables(page)

                pages.append({
                    "page_num": page_num + 1,
                    "text": text,
                    "tables": tables,
                    "has_tables": len(tables) > 0
                })

            logger.info(f"Extracted {len(pages)} pages from PDF")
            return pages

        finally:
            doc.close()

    def _extract_tables(self, page: fitz.Page) -> List[Dict[str, Any]]:
        """Extract tables from a PDF page.

        Args:
            page: PyMuPDF page object

        Returns:
            List of table dictionaries
        """
        tables = []
        # Basic table extraction - can be enhanced with more sophisticated methods
        try:
            page_dict = page.get_text("dict")
            blocks = page_dict.get("blocks", [])

            # Simple heuristic: look for blocks with structured layout
            # This is a simplified version - production would use more advanced table detection
            for block in blocks:
                if block.get("type") == 0:  # Text block
                    lines = block.get("lines", [])
                    if len(lines) > 2:  # Potential table
                        # Extract text from lines
                        table_text = []
                        for line in lines:
                            spans = line.get("spans", [])
                            line_text = " ".join(span.get("text", "") for span in spans)
                            if line_text.strip():
                                table_text.append(line_text.strip())

                        if table_text:
                            tables.append({
                                "type": "table",
                                "content": table_text
                            })
        except Exception as e:
            logger.warning(f"Error extracting tables: {e}")

        return tables

    def _detect_section(self, text: str) -> Optional[str]:
        """Detect section name from text.

        Args:
            text: Text chunk

        Returns:
            Detected section name or None
        """
        # Common Medicare handbook sections
        section_patterns = [
            r"(Part [ABCD])\s*[:\-]?\s*(.+)",
            r"(Section \d+)\s*[:\-]?\s*(.+)",
            r"(Chapter \d+)\s*[:\-]?\s*(.+)",
        ]

        for pattern in section_patterns:
            match = re.search(pattern, text[:200], re.IGNORECASE)
            if match:
                return " > ".join(match.groups())

        return None

    def _classify_chunk_type(self, text: str) -> str:
        """Classify chunk type based on content.

        Args:
            text: Text chunk

        Returns:
            Chunk type classification
        """
        text_lower = text.lower()

        # Classification rules based on keywords
        if any(word in text_lower for word in ["penalty", "late enrollment", "premium increase"]):
            return "penalty"
        elif any(word in text_lower for word in ["cost", "premium", "deductible", "$"]):
            return "cost"
        elif any(word in text_lower for word in ["enrollment", "enroll", "sign up", "register"]):
            return "enrollment"
        elif any(word in text_lower for word in ["coverage", "covered", "benefit"]):
            return "coverage"
        elif any(word in text_lower for word in ["eligibility", "eligible", "qualify"]):
            return "eligibility"
        else:
            return "general"

    def create_chunks(
        self,
        pages: List[Dict[str, Any]],
        doc_version: str = None
    ) -> List[Dict[str, Any]]:
        """Create chunks from extracted pages with metadata.

        Args:
            pages: List of page dictionaries from extract_pdf_content
            doc_version: Document version (default from settings)

        Returns:
            List of chunk dictionaries with metadata
        """
        doc_version = doc_version or settings.medicare_doc_version
        chunks = []
        chunk_id = 0

        logger.info(f"Creating chunks from {len(pages)} pages")

        for page_data in pages:
            page_num = page_data["page_num"]
            text = page_data["text"]

            # Skip empty pages
            if not text.strip():
                continue

            # Create text chunks
            text_chunks = self.text_splitter.split_text(text)

            for chunk_text in text_chunks:
                if len(chunk_text.strip()) < 50:  # Skip very short chunks
                    continue

                # Detect section
                section = self._detect_section(chunk_text)

                # Classify chunk type
                chunk_type = self._classify_chunk_type(chunk_text)

                chunk = {
                    "chunk_id": f"chunk_{doc_version}_{chunk_id}",
                    "content": chunk_text,
                    "metadata": {
                        "doc_version": doc_version,
                        "page_start": page_num,
                        "page_end": page_num,
                        "section": section or "2026 Medicare handbook",
                        "chunk_type": chunk_type,
                        "has_tables": page_data["has_tables"],
                    }
                }

                chunks.append(chunk)
                chunk_id += 1

            # Add table chunks separately
            for table in page_data.get("tables", []):
                table_text = "\n".join(table["content"])

                chunk = {
                    "chunk_id": f"chunk_{doc_version}_{chunk_id}_table",
                    "content": table_text,
                    "metadata": {
                        "doc_version": doc_version,
                        "page_start": page_num,
                        "page_end": page_num,
                        "section": "Table",
                        "chunk_type": "table",
                        "is_table": True,
                    }
                }

                chunks.append(chunk)
                chunk_id += 1

        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    def process_pdf(self, pdf_path: str = None) -> List[Dict[str, Any]]:
        """Complete pipeline: extract and chunk PDF.

        Args:
            pdf_path: Path to PDF file (default from settings)

        Returns:
            List of chunks ready for indexing
        """
        pdf_path = pdf_path or settings.medicare_pdf_path

        logger.info(f"Processing PDF: {pdf_path}")

        # Extract pages
        pages = self.extract_pdf_content(pdf_path)

        # Create chunks
        chunks = self.create_chunks(pages)

        logger.info(f"PDF processing complete: {len(chunks)} chunks created")

        return chunks
