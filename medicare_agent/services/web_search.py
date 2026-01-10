"""Web search service using Tavily for finding information beyond the manual."""

from typing import List, Dict, Any, Optional
from medicare_agent.config import settings
from medicare_agent.models.schemas import Chunk
import logging
import os
import warnings

# Suppress langchain-tavily internal warnings
warnings.filterwarnings('ignore', message='.*shadows an attribute.*')

logger = logging.getLogger(__name__)


class WebSearchService:
    """Service for web search using Tavily when manual information is insufficient."""

    def __init__(self):
        """Initialize web search service with Tavily."""
        self.enabled = False
        self.tavily_search = None
        self.llm = None

        # Only initialize if API key is available
        if settings.tavily_api_key and settings.enable_web_search:
            try:
                # Use tavily-python directly for simpler API
                from tavily import TavilyClient
                from langchain_openai import ChatOpenAI

                self.tavily_search = TavilyClient(api_key=settings.tavily_api_key)
                self.max_results = settings.web_search_max_results
                self.llm = ChatOpenAI(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    temperature=0.3
                )
                self.enabled = True
                logger.info("=" * 80)
                logger.info("🌐 [WEB SEARCH INIT] ✅ Web search service initialized successfully")
                logger.info(f"🌐 [WEB SEARCH INIT] Max results: {settings.web_search_max_results}")
                logger.info(f"🌐 [WEB SEARCH INIT] Service is ENABLED and ready")
                logger.info("=" * 80)
            except ImportError:
                logger.warning(
                    "tavily-python not installed. "
                    "Install with: pip install tavily-python"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize web search service: {e}")
        else:
            logger.info("=" * 80)
            logger.info("🌐 [WEB SEARCH INIT] ⚠️  Web search service DISABLED")
            if not settings.tavily_api_key:
                logger.info("🌐 [WEB SEARCH INIT] Reason: No TAVILY_API_KEY found")
            if not settings.enable_web_search:
                logger.info("🌐 [WEB SEARCH INIT] Reason: ENABLE_WEB_SEARCH is set to False")
            logger.info("=" * 80)

    def search(self, query: str) -> List[Chunk]:
        """Search the web for relevant information.

        Args:
            query: Search query

        Returns:
            List of Chunk objects with web search results
        """
        if not self.enabled or not self.tavily_search:
            logger.warning("🌐 [WEB SEARCH] ❌ Web search is disabled or not initialized")
            return []

        try:
            logger.info(f"🌐 [WEB SEARCH] 🔍 Calling Tavily API...")
            logger.info(f"🌐 [WEB SEARCH] Query: {query}")

            # Perform Tavily search using the client directly
            search_results = self.tavily_search.search(
                query=query,
                max_results=self.max_results
            )

            # Extract results from the response
            if isinstance(search_results, dict) and 'results' in search_results:
                results_list = search_results['results']
            elif isinstance(search_results, list):
                results_list = search_results
            else:
                logger.error(f"🌐 [WEB SEARCH] ❌ Unexpected result format: {type(search_results)}")
                return []

            logger.info(f"🌐 [WEB SEARCH] ✅ Tavily API returned {len(results_list)} results")

            # Convert search results to Chunk format
            chunks = []
            for idx, result in enumerate(results_list):
                if not isinstance(result, dict):
                    logger.warning(f"🌐 [WEB SEARCH] ⚠️  Skipping non-dict result at index {idx}")
                    continue

                url = result.get("url", "")
                title = result.get("title", "")
                content = result.get("content", "")

                logger.info(f"🌐 [WEB SEARCH] Result {idx+1}: {title[:50]}... from {url}")

                chunk = Chunk(
                    chunk_id=f"web_search_{idx}",
                    content=content,
                    metadata={
                        "source": "web_search",
                        "url": url,
                        "title": title,
                        "doc_version": "web",
                        "page": 0,
                        "section": "Web Search Result"
                    },
                    score=result.get("score", 0.0)
                )
                chunks.append(chunk)

            logger.info(f"🌐 [WEB SEARCH] ✅ Successfully converted {len(chunks)} results to chunks")
            return chunks

        except Exception as e:
            logger.error(f"🌐 [WEB SEARCH] ❌ ERROR: Web search failed - {str(e)}")
            logger.exception(e)
            return []

    def should_perform_web_search(
        self,
        query: str,
        retrieved_chunks: List[Chunk],
        min_chunks: int = 3,
        min_score: float = 0.5
    ) -> bool:
        """Determine if web search is needed based on retrieval quality.

        Args:
            query: User query
            retrieved_chunks: Chunks retrieved from manual
            min_chunks: Minimum number of quality chunks expected
            min_score: Minimum relevance score threshold

        Returns:
            True if web search should be performed
        """
        logger.info("🔍 [WEB SEARCH CHECK] Evaluating if web search is needed...")

        if not self.enabled:
            logger.info("🔍 [WEB SEARCH CHECK] ❌ Web search service is DISABLED")
            return False

        if not settings.enable_web_search:
            logger.info("🔍 [WEB SEARCH CHECK] ❌ Web search is DISABLED in config")
            return False

        logger.info(f"🔍 [WEB SEARCH CHECK] Web search service is ENABLED and ready")
        logger.info(f"🔍 [WEB SEARCH CHECK] Total chunks received: {len(retrieved_chunks)}")

        # Check if we have enough high-quality chunks
        high_quality_chunks = [
            chunk for chunk in retrieved_chunks
            if chunk.score and chunk.score >= min_score
        ]

        logger.info(f"🔍 [WEB SEARCH CHECK] High-quality chunks (score >= {min_score}): {len(high_quality_chunks)}")
        logger.info(f"🔍 [WEB SEARCH CHECK] Threshold: {min_chunks} chunks required")

        if len(high_quality_chunks) < min_chunks:
            logger.info(
                f"🔍 [WEB SEARCH CHECK] ✅ TRIGGERING WEB SEARCH: "
                f"Only {len(high_quality_chunks)} high-quality chunks found (need {min_chunks})"
            )
            return True

        logger.info(
            f"🔍 [WEB SEARCH CHECK] ❌ SKIPPING WEB SEARCH: "
            f"Sufficient manual information ({len(high_quality_chunks)} >= {min_chunks})"
        )
        return False

    def synthesize_with_web_results(
        self,
        query: str,
        manual_chunks: List[Chunk],
        web_chunks: List[Chunk]
    ) -> str:
        """Synthesize information from both manual and web sources.

        Args:
            query: User query
            manual_chunks: Chunks from Medicare manual
            web_chunks: Chunks from web search

        Returns:
            Synthesized context combining both sources
        """
        if not self.enabled or not self.llm:
            # Fallback: simple concatenation
            return f"Manual: {self._format_chunks(manual_chunks)}\n\nWeb: {self._format_chunks(web_chunks)}"

        synthesis_prompt = f"""You are synthesizing information from both Medicare manual and web sources.

User Query: {query}

Medicare Manual Information:
{self._format_chunks(manual_chunks)}

Web Search Results:
{self._format_chunks(web_chunks)}

Create a comprehensive summary that combines information from both sources.
Prioritize information from the Medicare manual when available.
Use web sources to supplement or provide additional context.
Keep the synthesis concise and relevant to the query.
"""

        try:
            response = self.llm.invoke(synthesis_prompt)
            return response.content
        except Exception as e:
            logger.error(f"Synthesis failed: {str(e)}")
            # Fallback: simple concatenation
            return f"Manual: {self._format_chunks(manual_chunks)}\n\nWeb: {self._format_chunks(web_chunks)}"

    def _format_chunks(self, chunks: List[Chunk]) -> str:
        """Format chunks for prompt.

        Args:
            chunks: List of chunks to format

        Returns:
            Formatted string representation
        """
        if not chunks:
            return "No information available."

        formatted = []
        for chunk in chunks:
            source_info = chunk.metadata.get("url", chunk.metadata.get("section", "2026 Medicare handbook"))
            formatted.append(f"- {chunk.content} (Source: {source_info})")

        return "\n".join(formatted)
