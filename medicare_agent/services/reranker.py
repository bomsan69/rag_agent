"""Reranking service for evidence selection."""

from typing import List
from medicare_agent.config import settings
from medicare_agent.models.schemas import Chunk
import logging

logger = logging.getLogger(__name__)


class RerankerService:
    """Service for reranking retrieved chunks to select best evidence."""

    def __init__(self):
        """Initialize reranker service."""
        pass  # No LLM needed for optimized reranking

    def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int = None
    ) -> List[Chunk]:
        """Rerank chunks based on relevance to query.

        Args:
            query: User query
            chunks: List of candidate chunks
            top_k: Number of top chunks to return (default from settings)

        Returns:
            Reranked list of top-k chunks
        """
        top_k = top_k or settings.top_k_rerank

        if len(chunks) <= top_k:
            return chunks

        logger.info(f"Reranking {len(chunks)} chunks to select top {top_k}")

        # Score each chunk efficiently (no LLM calls)
        for chunk in chunks:
            if chunk.score is None:
                chunk.score = 0.0

            # Apply type boost
            boost = self._get_type_boost(chunk)
            chunk.score = chunk.score * boost

        # Sort by score and return top-k
        chunks.sort(key=lambda x: x.score or 0, reverse=True)
        top_chunks = chunks[:top_k]

        logger.info(f"Reranking complete. Selected top {len(top_chunks)} chunks")
        return top_chunks

    def _get_type_boost(self, chunk: Chunk) -> float:
        """Get boost factor based on chunk type.

        Args:
            chunk: Chunk to get boost for

        Returns:
            Boost multiplier
        """
        chunk_type = chunk.metadata.get("chunk_type", "general")

        # Priority boost for specific chunk types
        type_boost = {
            "penalty": 1.3,
            "cost": 1.25,
            "table": 1.25,
            "enrollment": 1.15,
            "eligibility": 1.15,
        }.get(chunk_type, 1.0)

        return type_boost


    def select_best_evidence(
        self,
        query: str,
        chunks: List[Chunk],
        intent: str = "general"
    ) -> List[Chunk]:
        """Select best evidence chunks with intent-aware filtering.

        Args:
            query: User query
            chunks: Candidate chunks
            intent: Query intent (penalty, cost, enrollment, etc.)

        Returns:
            Filtered and reranked chunks
        """
        logger.info(f"Selecting evidence for intent: {intent}")

        # Filter by intent if specified
        if intent != "general":
            intent_filtered = [
                chunk for chunk in chunks
                if chunk.metadata.get("chunk_type") == intent
                or chunk.metadata.get("chunk_type") == "general"
            ]

            # Fall back to all chunks if intent filter is too restrictive
            if len(intent_filtered) >= 3:
                chunks = intent_filtered
                logger.info(f"Filtered to {len(chunks)} chunks matching intent")

        # Prioritize tables for cost and penalty queries
        if intent in ["cost", "penalty"]:
            table_chunks = [
                chunk for chunk in chunks
                if chunk.metadata.get("is_table") or "table" in chunk.metadata.get("chunk_type", "").lower()
            ]

            if table_chunks:
                logger.info(f"Prioritizing {len(table_chunks)} table chunks for {intent} query")
                # Put table chunks first
                non_table_chunks = [c for c in chunks if c not in table_chunks]
                chunks = table_chunks + non_table_chunks

        # Rerank
        return self.rerank(query, chunks)
