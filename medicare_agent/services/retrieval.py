"""Hybrid retrieval service using BM25 and vector search."""

import pickle
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi
import faiss
from langchain_openai import OpenAIEmbeddings
from medicare_agent.config import settings
from medicare_agent.models.schemas import Chunk
import logging

logger = logging.getLogger(__name__)


class RetrievalService:
    """Hybrid retrieval service combining BM25 and vector search."""

    def __init__(self):
        """Initialize retrieval service."""
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key
        )
        self.chunks: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.vector_index: Optional[faiss.IndexFlatL2] = None
        self.index_path = Path(settings.index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)

    def build_index(self, chunks: List[Dict[str, Any]]) -> None:
        """Build BM25 and vector indexes from chunks.

        Args:
            chunks: List of chunk dictionaries with content and metadata
        """
        logger.info(f"Building indexes for {len(chunks)} chunks")

        self.chunks = chunks

        # Build BM25 index
        logger.info("Building BM25 index...")
        tokenized_corpus = [chunk["content"].lower().split() for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # Build vector index
        logger.info("Building vector index with OpenAI embeddings...")
        texts = [chunk["content"] for chunk in chunks]

        # Generate embeddings in batches to avoid rate limits
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Embedding batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")
            batch_embeddings = self.embeddings.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)

        # Convert to numpy array
        embeddings_array = np.array(all_embeddings, dtype=np.float32)

        # Create FAISS index
        dimension = embeddings_array.shape[1]
        self.vector_index = faiss.IndexFlatL2(dimension)
        self.vector_index.add(embeddings_array)

        logger.info(f"Indexes built successfully. Vector dimension: {dimension}")

    def save_index(self, name: str = "medicare_index") -> None:
        """Save indexes to disk.

        Args:
            name: Base name for index files
        """
        logger.info(f"Saving indexes to {self.index_path}")

        # Save chunks
        chunks_path = self.index_path / f"{name}_chunks.pkl"
        with open(chunks_path, "wb") as f:
            pickle.dump(self.chunks, f)

        # Save BM25 index
        bm25_path = self.index_path / f"{name}_bm25.pkl"
        with open(bm25_path, "wb") as f:
            pickle.dump(self.bm25, f)

        # Save FAISS index
        faiss_path = self.index_path / f"{name}_faiss.index"
        faiss.write_index(self.vector_index, str(faiss_path))

        logger.info("Indexes saved successfully")

    def load_index(self, name: str = "medicare_index") -> None:
        """Load indexes from disk.

        Args:
            name: Base name for index files
        """
        logger.info(f"Loading indexes from {self.index_path}")

        # Load chunks
        chunks_path = self.index_path / f"{name}_chunks.pkl"
        with open(chunks_path, "rb") as f:
            self.chunks = pickle.load(f)

        # Load BM25 index
        bm25_path = self.index_path / f"{name}_bm25.pkl"
        with open(bm25_path, "rb") as f:
            self.bm25 = pickle.load(f)

        # Load FAISS index
        faiss_path = self.index_path / f"{name}_faiss.index"
        self.vector_index = faiss.read_index(str(faiss_path))

        logger.info(f"Indexes loaded successfully. {len(self.chunks)} chunks available")

    def _filter_chunks(
        self,
        chunks: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter chunks based on metadata filters.

        Args:
            chunks: List of chunks to filter
            filters: Dictionary of metadata filters

        Returns:
            Filtered list of chunks
        """
        if not filters:
            return chunks

        filtered = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            match = True

            for key, value in filters.items():
                if metadata.get(key) != value:
                    match = False
                    break

            if match:
                filtered.append(chunk)

        return filtered

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        filters: Optional[Dict[str, Any]] = None,
        bm25_weight: float = None,
        vector_weight: float = None
    ) -> List[Chunk]:
        """Retrieve relevant chunks using hybrid search.

        Args:
            query: Search query
            top_k: Number of chunks to retrieve
            filters: Metadata filters (e.g., doc_version, chunk_type)
            bm25_weight: Weight for BM25 scores (0-1), defaults from settings
            vector_weight: Weight for vector scores (0-1), defaults from settings

        Returns:
            List of Chunk objects with scores
        """
        if self.bm25 is None or self.vector_index is None:
            raise ValueError("Indexes not loaded. Call load_index() or build_index() first.")

        top_k = top_k or settings.top_k_retrieval
        bm25_weight = bm25_weight if bm25_weight is not None else settings.bm25_weight
        vector_weight = vector_weight if vector_weight is not None else settings.vector_weight

        logger.info(f"Retrieving top {top_k} chunks for query: {query[:100]}... (BM25: {bm25_weight}, Vector: {vector_weight})")

        # Apply filters first
        filtered_chunks = self._filter_chunks(self.chunks, filters or {})

        if not filtered_chunks:
            logger.warning("No chunks match the filters")
            return []

        # Get indices of filtered chunks
        filtered_indices = [
            i for i, chunk in enumerate(self.chunks)
            if chunk in filtered_chunks
        ]

        # BM25 search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)

        # Normalize BM25 scores
        bm25_max = max(bm25_scores) if max(bm25_scores) > 0 else 1
        bm25_scores_normalized = bm25_scores / bm25_max

        # Vector search
        query_embedding = self.embeddings.embed_query(query)
        query_vector = np.array([query_embedding], dtype=np.float32)

        # Search in full index
        distances, indices = self.vector_index.search(query_vector, len(self.chunks))

        # Normalize vector scores (convert distances to similarities)
        max_distance = max(distances[0]) if max(distances[0]) > 0 else 1
        vector_scores = 1 - (distances[0] / max_distance)

        # Combine scores for filtered chunks only
        combined_scores = {}
        for idx in filtered_indices:
            bm25_score = bm25_scores_normalized[idx] * bm25_weight
            vector_score = vector_scores[idx] * vector_weight
            combined_scores[idx] = bm25_score + vector_score

        # Sort by combined score
        sorted_indices = sorted(
            combined_scores.keys(),
            key=lambda x: combined_scores[x],
            reverse=True
        )

        # Get top-k chunks
        top_indices = sorted_indices[:top_k]

        results = []
        for idx in top_indices:
            chunk_data = self.chunks[idx]
            chunk = Chunk(
                chunk_id=chunk_data["chunk_id"],
                content=chunk_data["content"],
                metadata=chunk_data["metadata"],
                score=float(combined_scores[idx])
            )
            results.append(chunk)

        logger.info(f"Retrieved {len(results)} chunks")
        return results

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """Get a specific chunk by ID.

        Args:
            chunk_id: Chunk identifier

        Returns:
            Chunk object or None if not found
        """
        for chunk_data in self.chunks:
            if chunk_data["chunk_id"] == chunk_id:
                return Chunk(
                    chunk_id=chunk_data["chunk_id"],
                    content=chunk_data["content"],
                    metadata=chunk_data["metadata"]
                )
        return None
