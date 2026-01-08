"""Script to build search index from Medicare PDF."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from medicare_agent.services.ingestion import IngestionService
from medicare_agent.services.retrieval import RetrievalService
from medicare_agent.config import settings
from medicare_agent.utils.helpers import setup_logging, ensure_directory
import logging

logger = logging.getLogger(__name__)


def main():
    """Build index from Medicare PDF."""
    setup_logging(settings.log_level)
    logger.info("=" * 80)
    logger.info("Medicare AI Chatbot - Index Builder")
    logger.info("=" * 80)

    # Check if PDF exists
    pdf_path = Path(settings.medicare_pdf_path)
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        logger.error("Please ensure medicare_manual.pdf is in the docs/ folder")
        sys.exit(1)

    logger.info(f"PDF Path: {pdf_path}")
    logger.info(f"Doc Version: {settings.medicare_doc_version}")
    logger.info(f"Index Path: {settings.index_path}")

    # Ensure index directory exists
    ensure_directory(settings.index_path)

    try:
        # Step 1: Ingest PDF
        logger.info("\nStep 1: Ingesting PDF and creating chunks...")
        ingestion = IngestionService()
        chunks = ingestion.process_pdf(str(pdf_path))

        logger.info(f"✓ Created {len(chunks)} chunks from PDF")

        # Step 2: Build indexes
        logger.info("\nStep 2: Building search indexes (BM25 + Vector)...")
        logger.info("⚠ This may take several minutes due to OpenAI API rate limits")

        retrieval = RetrievalService()
        retrieval.build_index(chunks)

        logger.info("✓ Indexes built successfully")

        # Step 3: Save indexes
        logger.info("\nStep 3: Saving indexes to disk...")
        retrieval.save_index(name="medicare_index")

        logger.info("✓ Indexes saved successfully")

        logger.info("\n" + "=" * 80)
        logger.info("Index building complete!")
        logger.info("=" * 80)
        logger.info(f"\nIndex files saved to: {settings.index_path}")
        logger.info("\nYou can now start the API server:")
        logger.info("  python -m uvicorn medicare_agent.app:app --reload")

    except Exception as e:
        logger.error(f"\n✗ Error building index: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
