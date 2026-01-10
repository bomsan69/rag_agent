"""Agent orchestrator using LangGraph for RAG pipeline."""

from typing import TypedDict, Annotated, Sequence, AsyncIterator, List, Dict, Any
from langgraph.graph import StateGraph, END
from medicare_agent.services.retrieval import RetrievalService
from medicare_agent.services.reranker import RerankerService
from medicare_agent.services.generator import GeneratorService
from medicare_agent.services.verifier import VerifierService
from medicare_agent.services.web_search import WebSearchService
from medicare_agent.services.conversation_history import ConversationHistoryService
from medicare_agent.models.schemas import Chunk, Citation, ChatResponse
from medicare_agent.config import settings
import logging

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for agent orchestration."""
    query: str
    session_id: str
    doc_version: str
    intent: str
    expanded_query: str
    retrieved_chunks: list[Chunk]
    reranked_chunks: list[Chunk]
    web_search_chunks: list[Chunk]
    needs_web_search: bool
    combined_chunks: list[Chunk]
    draft_answer: str
    final_answer: str
    citations: list[Citation]
    confidence: str
    issues: list[str]
    needs_revision: bool
    revision_count: int
    conversation_history: list[Dict[str, str]]


class AgentOrchestrator:
    """Orchestrates the RAG pipeline using LangGraph."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        reranker_service: RerankerService,
        generator_service: GeneratorService,
        verifier_service: VerifierService,
        web_search_service: WebSearchService = None,
        conversation_history_service: ConversationHistoryService = None
    ):
        """Initialize orchestrator.

        Args:
            retrieval_service: Retrieval service instance
            reranker_service: Reranker service instance
            generator_service: Generator service instance
            verifier_service: Verifier service instance
            web_search_service: Web search service instance (optional)
            conversation_history_service: Conversation history service instance (optional)
        """
        self.retrieval = retrieval_service
        self.reranker = reranker_service
        self.generator = generator_service
        self.verifier = verifier_service
        self.web_search = web_search_service or WebSearchService()
        self.conversation_history = conversation_history_service or ConversationHistoryService()
        self.graph = self._build_graph()

    def _classify_intent(self, state: AgentState) -> AgentState:
        """Classify user intent."""
        if settings.enable_intent_classification:
            logger.info("Node: Classifying intent")
            intent = self.generator.classify_intent(state["query"])
            state["intent"] = intent
        else:
            logger.info("Node: Skipping intent classification (disabled)")
            state["intent"] = "general"
        return state

    def _expand_query(self, state: AgentState) -> AgentState:
        """Expand query with Medicare terminology."""
        if settings.enable_query_expansion:
            logger.info("Node: Expanding query")
            expanded = self.generator.expand_query(state["query"])
            state["expanded_query"] = expanded
        else:
            logger.info("Node: Skipping query expansion (disabled)")
            state["expanded_query"] = state["query"]
        return state

    def _retrieve(self, state: AgentState) -> AgentState:
        """Retrieve relevant chunks."""
        logger.info("Node: Retrieving chunks")

        filters = {
            "doc_version": state.get("doc_version", "2026")
        }

        # Use expanded query if available
        query = state.get("expanded_query") or state["query"]

        chunks = self.retrieval.retrieve(
            query=query,
            filters=filters
        )

        state["retrieved_chunks"] = chunks
        return state

    def _rerank(self, state: AgentState) -> AgentState:
        """Rerank retrieved chunks."""
        logger.info("Node: Reranking chunks")

        chunks = state["retrieved_chunks"]
        intent = state["intent"]
        query = state["query"]

        reranked = self.reranker.select_best_evidence(
            query=query,
            chunks=chunks,
            intent=intent
        )

        state["reranked_chunks"] = reranked
        logger.info(f"Reranked to {len(reranked)} chunks")

        # Check if web search is needed
        logger.info("=" * 80)
        logger.info("CHECKING IF WEB SEARCH IS NEEDED")
        logger.info(f"Query: {query}")
        logger.info(f"Number of reranked chunks: {len(reranked)}")
        if reranked:
            scores = [chunk.score for chunk in reranked if chunk.score]
            if scores:
                logger.info(f"Chunk scores: min={min(scores):.3f}, max={max(scores):.3f}, avg={sum(scores)/len(scores):.3f}")
            else:
                logger.info("No scores available for chunks")

        # Use more aggressive thresholds to trigger web search more easily
        # For location-specific or provider-specific queries, we need web search
        state["needs_web_search"] = self.web_search.should_perform_web_search(
            query=query,
            retrieved_chunks=reranked,
            min_chunks=5,  # Increased from 3 - need more high-quality chunks to skip web search
            min_score=0.6  # Increased from 0.5 - need higher relevance to skip web search
        )

        logger.info(f"Web search needed: {state['needs_web_search']}")
        logger.info("=" * 80)

        return state

    def _web_search(self, state: AgentState) -> AgentState:
        """Perform web search for additional information."""
        logger.info("=" * 80)
        logger.info("🌐 [WEB SEARCH NODE] EXECUTING WEB SEARCH")
        logger.info("=" * 80)

        query = state["query"]
        logger.info(f"🌐 [WEB SEARCH NODE] Searching the web for: {query}")

        web_chunks = self.web_search.search(query)

        state["web_search_chunks"] = web_chunks

        # Combine manual chunks with web search results
        state["combined_chunks"] = state["reranked_chunks"] + web_chunks

        logger.info(f"🌐 [WEB SEARCH NODE] Web search returned {len(web_chunks)} chunks")
        logger.info(f"🌐 [WEB SEARCH NODE] Combined {len(state['reranked_chunks'])} manual chunks + {len(web_chunks)} web chunks")
        logger.info(f"🌐 [WEB SEARCH NODE] Total chunks for generation: {len(state['combined_chunks'])}")
        logger.info("=" * 80)
        return state

    def _should_web_search(self, state: AgentState) -> str:
        """Decide if web search is needed."""
        needs_search = state.get("needs_web_search", False)

        logger.info("=" * 80)
        logger.info("🔀 [CONDITIONAL EDGE] Making routing decision...")
        logger.info(f"🔀 [CONDITIONAL EDGE] needs_web_search flag: {needs_search}")

        if needs_search:
            logger.info("🔀 [CONDITIONAL EDGE] ➡️  ROUTING TO: web_search node")
            logger.info("=" * 80)
            return "web_search"
        else:
            logger.info("🔀 [CONDITIONAL EDGE] ➡️  ROUTING TO: generate node (skipping web search)")
            logger.info("=" * 80)
            return "generate"

    def _generate(self, state: AgentState) -> AgentState:
        """Generate answer from evidence."""
        logger.info("Node: Generating answer")

        # Use combined chunks if web search was performed, otherwise use reranked chunks
        evidence_chunks = state.get("combined_chunks") or state["reranked_chunks"]

        # Get conversation history from state
        conversation_history = state.get("conversation_history", [])

        answer, citations = self.generator.generate(
            query=state["query"],
            evidence_chunks=evidence_chunks,
            intent=state["intent"],
            conversation_history=conversation_history
        )

        state["draft_answer"] = answer
        state["citations"] = citations
        return state

    def _verify(self, state: AgentState) -> AgentState:
        """Verify answer accuracy."""
        if not settings.enable_verification:
            logger.info("Node: Skipping verification (disabled)")
            state["final_answer"] = state["draft_answer"]
            state["issues"] = []
            state["confidence"] = "medium"
            state["needs_revision"] = False
            return state

        logger.info("Node: Verifying answer")

        approved, revised_answer, issues, confidence = self.verifier.verify(
            draft_answer=state["draft_answer"],
            citations=state["citations"],
            evidence_chunks=state["reranked_chunks"]
        )

        state["final_answer"] = revised_answer
        state["issues"] = issues
        state["confidence"] = confidence
        state["needs_revision"] = not approved and state.get("revision_count", 0) < 2

        if state["needs_revision"]:
            state["revision_count"] = state.get("revision_count", 0) + 1

        return state

    def _should_revise(self, state: AgentState) -> str:
        """Decide if answer needs revision."""
        if state.get("needs_revision", False):
            logger.info("Decision: Needs revision, returning to generate")
            return "generate"
        else:
            logger.info("Decision: Answer approved, ending")
            return "end"

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("expand_query", self._expand_query)
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("rerank", self._rerank)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("generate", self._generate)
        workflow.add_node("verify", self._verify)

        # Add edges
        workflow.set_entry_point("classify_intent")
        workflow.add_edge("classify_intent", "expand_query")
        workflow.add_edge("expand_query", "retrieve")
        workflow.add_edge("retrieve", "rerank")

        # Conditional edge: web search or directly to generate
        workflow.add_conditional_edges(
            "rerank",
            self._should_web_search,
            {
                "web_search": "web_search",
                "generate": "generate"
            }
        )

        workflow.add_edge("web_search", "generate")
        workflow.add_edge("generate", "verify")

        # Conditional edge: revise or end
        workflow.add_conditional_edges(
            "verify",
            self._should_revise,
            {
                "generate": "generate",
                "end": END
            }
        )

        return workflow.compile()

    def process_query(
        self,
        query: str,
        session_id: str,
        doc_version: str = "2026"
    ) -> ChatResponse:
        """Process user query through RAG pipeline.

        Args:
            query: User query
            session_id: Session identifier
            doc_version: Document version

        Returns:
            ChatResponse with answer and citations
        """
        logger.info(f"Processing query: {query[:100]}...")
        logger.info(f"Session ID: {session_id[:8]}...")

        # Load conversation history
        conversation_history = self.conversation_history.get_recent_messages_for_context(session_id)
        if conversation_history:
            logger.info(f"💬 Using conversation history: {len(conversation_history)} previous messages loaded from Redis")
        else:
            logger.info(f"💬 New conversation: No previous history found")

        # Add current user query to history
        self.conversation_history.add_message(session_id, "user", query)

        # Initial state
        initial_state = AgentState(
            query=query,
            session_id=session_id,
            doc_version=doc_version,
            intent="",
            expanded_query="",
            retrieved_chunks=[],
            reranked_chunks=[],
            web_search_chunks=[],
            needs_web_search=False,
            combined_chunks=[],
            draft_answer="",
            final_answer="",
            citations=[],
            confidence="medium",
            issues=[],
            needs_revision=False,
            revision_count=0,
            conversation_history=conversation_history
        )

        # Run graph
        final_state = self.graph.invoke(initial_state)

        # Build response
        response = ChatResponse(
            answer=final_state["final_answer"],
            citations=final_state["citations"],
            confidence=final_state["confidence"]
        )

        # Add assistant response to history
        self.conversation_history.add_message(
            session_id,
            "assistant",
            response.answer,
            metadata={
                "citations": [c.dict() for c in response.citations],
                "confidence": response.confidence
            }
        )

        logger.info(f"Query processed. Confidence: {response.confidence}")
        return response

    async def process_query_stream(
        self,
        query: str,
        session_id: str,
        doc_version: str = "2026"
    ) -> AsyncIterator[str]:
        """Process query with streaming response.

        Args:
            query: User query
            session_id: Session identifier
            doc_version: Document version

        Yields:
            Answer chunks as they're generated
        """
        logger.info(f"Processing query with streaming: {query[:100]}...")
        logger.info(f"Session ID: {session_id[:8]}...")

        # Load conversation history
        conversation_history = self.conversation_history.get_recent_messages_for_context(session_id)
        if conversation_history:
            logger.info(f"💬 [STREAMING] Using conversation history: {len(conversation_history)} previous messages loaded from Redis")
        else:
            logger.info(f"💬 [STREAMING] New conversation: No previous history found")

        # Add current user query to history
        self.conversation_history.add_message(session_id, "user", query)

        # Run pipeline up to generation (skip verification in streaming mode)
        # Use settings to determine if we should classify/expand
        if settings.enable_intent_classification:
            intent = self.generator.classify_intent(query)
        else:
            intent = "general"

        if settings.enable_query_expansion:
            expanded_query = self.generator.expand_query(query)
        else:
            expanded_query = query

        filters = {"doc_version": doc_version}
        chunks = self.retrieval.retrieve(query=expanded_query, filters=filters)

        reranked = self.reranker.select_best_evidence(
            query=query,
            chunks=chunks,
            intent=intent
        )

        # Check if web search is needed (same logic as non-streaming)
        logger.info("=" * 80)
        logger.info("CHECKING IF WEB SEARCH IS NEEDED (STREAMING MODE)")
        logger.info(f"Query: {query}")
        logger.info(f"Number of reranked chunks: {len(reranked)}")
        if reranked:
            scores = [chunk.score for chunk in reranked if chunk.score]
            if scores:
                logger.info(f"Chunk scores: min={min(scores):.3f}, max={max(scores):.3f}, avg={sum(scores)/len(scores):.3f}")
            else:
                logger.info("No scores available for chunks")

        needs_web_search = self.web_search.should_perform_web_search(
            query=query,
            retrieved_chunks=reranked,
            min_chunks=5,
            min_score=0.6
        )

        logger.info(f"Web search needed: {needs_web_search}")
        logger.info("=" * 80)

        # Perform web search if needed
        evidence_chunks = reranked
        if needs_web_search:
            logger.info("=" * 80)
            logger.info("🌐 [STREAMING] EXECUTING WEB SEARCH")
            logger.info("=" * 80)
            web_chunks = self.web_search.search(query)
            evidence_chunks = reranked + web_chunks
            logger.info(f"🌐 [STREAMING] Combined {len(reranked)} manual + {len(web_chunks)} web = {len(evidence_chunks)} total chunks")
            logger.info("=" * 80)

        # Accumulate answer for history
        full_answer = ""

        # Stream generation (verification skipped for speed)
        async for chunk in self.generator.generate_stream(
            query=query,
            evidence_chunks=evidence_chunks,
            intent=intent,
            conversation_history=conversation_history
        ):
            full_answer += chunk
            yield chunk

        # Add assistant response to history after streaming completes
        self.conversation_history.add_message(session_id, "assistant", full_answer)
