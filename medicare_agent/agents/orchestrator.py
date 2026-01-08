"""Agent orchestrator using LangGraph for RAG pipeline."""

from typing import TypedDict, Annotated, Sequence, AsyncIterator
from langgraph.graph import StateGraph, END
from medicare_agent.services.retrieval import RetrievalService
from medicare_agent.services.reranker import RerankerService
from medicare_agent.services.generator import GeneratorService
from medicare_agent.services.verifier import VerifierService
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
    draft_answer: str
    final_answer: str
    citations: list[Citation]
    confidence: str
    issues: list[str]
    needs_revision: bool
    revision_count: int


class AgentOrchestrator:
    """Orchestrates the RAG pipeline using LangGraph."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        reranker_service: RerankerService,
        generator_service: GeneratorService,
        verifier_service: VerifierService
    ):
        """Initialize orchestrator.

        Args:
            retrieval_service: Retrieval service instance
            reranker_service: Reranker service instance
            generator_service: Generator service instance
            verifier_service: Verifier service instance
        """
        self.retrieval = retrieval_service
        self.reranker = reranker_service
        self.generator = generator_service
        self.verifier = verifier_service
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
        return state

    def _generate(self, state: AgentState) -> AgentState:
        """Generate answer from evidence."""
        logger.info("Node: Generating answer")

        answer, citations = self.generator.generate(
            query=state["query"],
            evidence_chunks=state["reranked_chunks"],
            intent=state["intent"]
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
        workflow.add_node("generate", self._generate)
        workflow.add_node("verify", self._verify)

        # Add edges
        workflow.set_entry_point("classify_intent")
        workflow.add_edge("classify_intent", "expand_query")
        workflow.add_edge("expand_query", "retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", "generate")
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

        # Initial state
        initial_state = AgentState(
            query=query,
            session_id=session_id,
            doc_version=doc_version,
            intent="",
            expanded_query="",
            retrieved_chunks=[],
            reranked_chunks=[],
            draft_answer="",
            final_answer="",
            citations=[],
            confidence="medium",
            issues=[],
            needs_revision=False,
            revision_count=0
        )

        # Run graph
        final_state = self.graph.invoke(initial_state)

        # Build response
        response = ChatResponse(
            answer=final_state["final_answer"],
            citations=final_state["citations"],
            confidence=final_state["confidence"]
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

        # Stream generation (verification skipped for speed)
        async for chunk in self.generator.generate_stream(
            query=query,
            evidence_chunks=reranked,
            intent=intent
        ):
            yield chunk
