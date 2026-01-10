"""Pydantic models for API requests and responses."""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation information for answer verification."""
    section: str = Field(..., description="Section path in document")
    page: int = Field(..., description="Page number")
    doc_version: str = Field(..., description="Document version")
    chunk_id: Optional[str] = Field(None, description="Internal chunk identifier")


class ChatRequest(BaseModel):
    """Request model for /agent/chat endpoint."""
    session_id: str = Field(..., description="Session identifier for conversation tracking")
    user_query: str = Field(..., description="User's question about Medicare")
    doc_version: str = Field(default="2026", description="Medicare handbook version")
    stream: bool = Field(default=True, description="Enable streaming responses")


class ChatResponse(BaseModel):
    """Response model for /agent/chat endpoint."""
    answer: str = Field(..., description="Generated answer with citations")
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source citations supporting the answer"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ...,
        description="Confidence level of the answer"
    )


class Chunk(BaseModel):
    """Document chunk with metadata."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk text content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Chunk metadata (page, section, etc.)"
    )
    score: Optional[float] = Field(None, description="Relevance score")


class RetrievalRequest(BaseModel):
    """Request model for /retrieve endpoint."""
    queries: List[str] = Field(..., description="Search queries")
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Metadata filters (doc_version, chunk_type, etc.)"
    )
    top_k: int = Field(default=10, description="Number of chunks to retrieve")


class RetrievalResponse(BaseModel):
    """Response model for /retrieve endpoint."""
    chunks: List[Chunk] = Field(..., description="Retrieved document chunks")
    query_used: str = Field(..., description="Processed query used for retrieval")


class VerifyRequest(BaseModel):
    """Request model for /verify endpoint."""
    draft_answer: str = Field(..., description="Generated answer to verify")
    citations: List[Citation] = Field(..., description="Citations used in answer")


class VerifyResponse(BaseModel):
    """Response model for /verify endpoint."""
    approved: bool = Field(..., description="Whether answer is approved")
    revised_answer: Optional[str] = Field(
        None,
        description="Revised answer if modifications were needed"
    )
    issues: List[str] = Field(
        default_factory=list,
        description="List of issues found during verification"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ...,
        description="Confidence level after verification"
    )


class SessionCloseRequest(BaseModel):
    """Request model for /session/close endpoint."""
    session_id: str = Field(..., description="Session identifier to close")


class SessionCloseResponse(BaseModel):
    """Response model for /session/close endpoint."""
    success: bool = Field(..., description="Whether session was successfully closed")
    message: str = Field(..., description="Status message")
    session_id: str = Field(..., description="Session identifier that was closed")
