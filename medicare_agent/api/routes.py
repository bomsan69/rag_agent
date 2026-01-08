"""FastAPI routes for Medicare AI Chatbot."""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from medicare_agent.models.schemas import (
    ChatRequest,
    ChatResponse,
    RetrievalRequest,
    RetrievalResponse,
    VerifyRequest,
    VerifyResponse,
    Citation,
)
from medicare_agent.services.retrieval import RetrievalService
from medicare_agent.services.reranker import RerankerService
from medicare_agent.services.generator import GeneratorService
from medicare_agent.services.verifier import VerifierService
from medicare_agent.agents.orchestrator import AgentOrchestrator
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global service instances (will be initialized on startup)
_retrieval_service: Optional[RetrievalService] = None
_reranker_service: Optional[RerankerService] = None
_generator_service: Optional[GeneratorService] = None
_verifier_service: Optional[VerifierService] = None
_orchestrator: Optional[AgentOrchestrator] = None


def get_services():
    """Dependency to get initialized services."""
    global _retrieval_service, _reranker_service, _generator_service, _verifier_service, _orchestrator

    if not all([_retrieval_service, _reranker_service, _generator_service, _verifier_service, _orchestrator]):
        raise HTTPException(
            status_code=503,
            detail="Services not initialized. Please wait for startup to complete."
        )

    return {
        "retrieval": _retrieval_service,
        "reranker": _reranker_service,
        "generator": _generator_service,
        "verifier": _verifier_service,
        "orchestrator": _orchestrator,
    }


def initialize_services():
    """Initialize all services. Called on app startup."""
    global _retrieval_service, _reranker_service, _generator_service, _verifier_service, _orchestrator

    logger.info("Initializing services...")

    try:
        _retrieval_service = RetrievalService()
        _retrieval_service.load_index()

        _reranker_service = RerankerService()
        _generator_service = GeneratorService()
        _verifier_service = VerifierService()

        _orchestrator = AgentOrchestrator(
            retrieval_service=_retrieval_service,
            reranker_service=_reranker_service,
            generator_service=_generator_service,
            verifier_service=_verifier_service,
        )

        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


@router.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(
    request: ChatRequest,
    services: dict = Depends(get_services)
):
    """Process user query and return answer with citations.

    Args:
        request: Chat request with query and session info

    Returns:
        ChatResponse with answer, citations, and confidence
    """
    logger.info(f"Received chat request: {request.user_query[:100]}...")

    try:
        orchestrator: AgentOrchestrator = services["orchestrator"]

        if request.stream:
            # Return streaming response
            async def generate():
                # Send initial metadata
                yield {
                    "event": "start",
                    "data": json.dumps({"session_id": request.session_id})
                }

                # Stream answer
                async for chunk in orchestrator.process_query_stream(
                    query=request.user_query,
                    session_id=request.session_id,
                    doc_version=request.doc_version
                ):
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": chunk})
                    }

                # Send completion
                yield {
                    "event": "done",
                    "data": json.dumps({"status": "complete"})
                }

            return EventSourceResponse(generate())

        else:
            # Non-streaming response
            response = orchestrator.process_query(
                query=request.user_query,
                session_id=request.session_id,
                doc_version=request.doc_version
            )

            return response

    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve", response_model=RetrievalResponse)
async def retrieve(
    request: RetrievalRequest,
    services: dict = Depends(get_services)
):
    """Retrieve relevant document chunks.

    Args:
        request: Retrieval request with queries and filters

    Returns:
        RetrievalResponse with retrieved chunks
    """
    logger.info(f"Received retrieval request: {request.queries}")

    try:
        retrieval: RetrievalService = services["retrieval"]

        # Combine queries if multiple
        query = " ".join(request.queries)

        chunks = retrieval.retrieve(
            query=query,
            top_k=request.top_k,
            filters=request.filters
        )

        return RetrievalResponse(
            chunks=chunks,
            query_used=query
        )

    except Exception as e:
        logger.error(f"Error processing retrieval request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify", response_model=VerifyResponse)
async def verify(
    request: VerifyRequest,
    services: dict = Depends(get_services)
):
    """Verify answer accuracy and citations.

    Args:
        request: Verification request with answer and citations

    Returns:
        VerifyResponse with approval status and issues
    """
    logger.info("Received verification request")

    try:
        verifier: VerifierService = services["verifier"]
        retrieval: RetrievalService = services["retrieval"]

        # Get evidence chunks from citations
        evidence_chunks = []
        for citation in request.citations:
            if citation.chunk_id:
                chunk = retrieval.get_chunk_by_id(citation.chunk_id)
                if chunk:
                    evidence_chunks.append(chunk)

        if not evidence_chunks:
            return VerifyResponse(
                approved=False,
                issues=["No evidence chunks found for citations"],
                confidence="low"
            )

        # Verify
        approved, revised_answer, issues, confidence = verifier.verify(
            draft_answer=request.draft_answer,
            citations=request.citations,
            evidence_chunks=evidence_chunks
        )

        return VerifyResponse(
            approved=approved,
            revised_answer=revised_answer if revised_answer != request.draft_answer else None,
            issues=issues,
            confidence=confidence
        )

    except Exception as e:
        logger.error(f"Error processing verification request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "retrieval": _retrieval_service is not None,
            "reranker": _reranker_service is not None,
            "generator": _generator_service is not None,
            "verifier": _verifier_service is not None,
            "orchestrator": _orchestrator is not None,
        }
    }
