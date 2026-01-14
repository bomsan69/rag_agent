"""Conversation history management using LangGraph checkpoint."""

import logging
from typing import List, Dict, Any, Optional, TypedDict
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from medicare_agent.config import settings

logger = logging.getLogger(__name__)


class ConversationState(TypedDict):
    """State for conversation history."""
    messages: List[BaseMessage]


class ConversationHistoryService:
    """Manages conversation history storage and retrieval using LangGraph checkpoint."""

    def __init__(self, checkpoint_path: Optional[str] = None, use_memory: bool = True):
        """Initialize LangGraph checkpoint.

        Args:
            checkpoint_path: Path to SQLite checkpoint database (if use_memory=False).
                           Defaults to './data/checkpoints/conversations.db'
            use_memory: If True, use MemorySaver (in-memory, not persistent).
                       If False, use SqliteSaver (requires langgraph-checkpoint-sqlite).
                       Default: True
        """
        try:
            if use_memory:
                # Use in-memory checkpoint (not persistent across restarts)
                # Good for development and testing
                self.checkpointer = MemorySaver()
                self.sqlite_conn = None
                logger.info("✓ LangGraph checkpoint initialized: In-Memory Storage")
                logger.warning("⚠ Using MemorySaver - conversations will NOT persist across restarts")
            else:
                # Use SQLite checkpoint (persistent)
                # Requires: pip install langgraph-checkpoint-sqlite
                if checkpoint_path is None:
                    checkpoint_path = "./data/checkpoints/conversations.db"

                # Ensure directory exists
                db_path = Path(checkpoint_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)

                # NOTE: This requires langgraph-checkpoint-sqlite to be installed
                try:
                    import sqlite3
                    from langgraph.checkpoint.sqlite import SqliteSaver

                    # Create SQLite connection
                    self.sqlite_conn = sqlite3.connect(str(db_path), check_same_thread=False)
                    self.checkpointer = SqliteSaver(self.sqlite_conn)

                    # Initialize checkpoint tables
                    self.checkpointer.setup()

                    logger.info(f"✓ LangGraph checkpoint initialized: SQLite Storage ({checkpoint_path})")
                except ImportError:
                    logger.error("✗ SqliteSaver not available. Install with: uv pip install langgraph-checkpoint-sqlite")
                    logger.info("ℹ Falling back to MemorySaver")
                    self.checkpointer = MemorySaver()
                    self.sqlite_conn = None

            # Build a simple graph for message storage
            self._build_graph()

            logger.info(
                f"✓ Conversation history persistence: ENABLED "
                f"(max_messages={settings.max_conversation_messages})"
            )
        except Exception as e:
            logger.error(f"✗ Failed to initialize checkpoint: {e}")
            logger.warning("⚠ Conversation history will NOT be persisted - running in stateless mode")
            self.checkpointer = None
            self.graph = None

    def _build_graph(self):
        """Build a simple graph for message management."""

        def store_messages(state: ConversationState) -> ConversationState:
            """Simply return the state (messages are stored by checkpoint)."""
            return state

        workflow = StateGraph(ConversationState)
        workflow.add_node("store", store_messages)
        workflow.set_entry_point("store")
        workflow.add_edge("store", END)

        self.graph = workflow.compile(checkpointer=self.checkpointer)

    def _get_thread_config(self, session_id: str) -> Dict[str, Any]:
        """Get LangGraph thread configuration for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            Thread configuration dictionary
        """
        return {"configurable": {"thread_id": session_id}}

    def _message_to_langchain(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> BaseMessage:
        """Convert message dict to LangChain message object.

        Args:
            role: Message role ("user" or "assistant")
            content: Message content
            metadata: Optional metadata

        Returns:
            LangChain message object
        """
        additional_kwargs = {"metadata": metadata} if metadata else {}

        if role == "user":
            return HumanMessage(content=content, additional_kwargs=additional_kwargs)
        elif role == "assistant":
            return AIMessage(content=content, additional_kwargs=additional_kwargs)
        else:
            raise ValueError(f"Unknown role: {role}")

    def _langchain_message_to_dict(self, message: BaseMessage) -> Dict[str, Any]:
        """Convert LangChain message to dictionary format.

        Args:
            message: LangChain message object

        Returns:
            Message dictionary
        """
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        result = {
            "role": role,
            "content": message.content,
        }

        # Extract metadata if exists
        if hasattr(message, 'additional_kwargs') and message.additional_kwargs:
            metadata = message.additional_kwargs.get('metadata')
            if metadata:
                result["metadata"] = metadata

        return result

    def add_message(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to conversation history.

        Args:
            session_id: Unique session identifier
            role: Message role ("user" or "assistant")
            content: Message content
            metadata: Optional metadata (citations, confidence, etc.)

        Returns:
            True if successful, False otherwise
        """
        if not self.checkpointer or not self.graph:
            return False

        try:
            # Get current messages
            current_messages = self._get_messages_from_checkpoint(session_id)

            # Add new message
            new_message = self._message_to_langchain(role, content, metadata)
            current_messages.append(new_message)

            # Trim messages using LangChain's trim_messages
            # Keep last N messages (both user and assistant)
            max_messages = settings.max_conversation_messages * 2
            if len(current_messages) > max_messages:
                # Simple slice-based trimming (most reliable)
                current_messages = current_messages[-max_messages:]

            # Save to checkpoint using graph invoke
            config = self._get_thread_config(session_id)
            state = ConversationState(messages=current_messages)
            self.graph.invoke(state, config)

            logger.info(
                f"📝 [CHECKPOINT] Saved {role} message to session {session_id[:8]}... "
                f"(total: {len(current_messages)} messages, {len(content[:100])}... chars)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add message to checkpoint: {e}", exc_info=True)
            return False

    def _get_messages_from_checkpoint(self, session_id: str) -> List[BaseMessage]:
        """Get messages from checkpoint storage.

        Args:
            session_id: Unique session identifier

        Returns:
            List of LangChain message objects
        """
        if not self.checkpointer or not self.graph:
            return []

        try:
            config = self._get_thread_config(session_id)

            # Get state from checkpoint
            state = self.graph.get_state(config)

            if state and state.values and "messages" in state.values:
                return state.values["messages"]

            return []

        except Exception as e:
            logger.error(f"Failed to get messages from checkpoint: {e}")
            return []

    def get_history(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a session.

        Args:
            session_id: Unique session identifier
            limit: Maximum number of recent messages to return (None = all)

        Returns:
            List of message dictionaries
        """
        if not self.checkpointer:
            return []

        try:
            messages = self._get_messages_from_checkpoint(session_id)

            # Convert to dict format
            history = [self._langchain_message_to_dict(msg) for msg in messages]

            # Apply limit if specified
            if limit is not None and limit > 0:
                history = history[-limit:]

            if history:
                logger.info(f"📖 [CHECKPOINT] Retrieved {len(history)} messages for session {session_id[:8]}...")
            return history

        except Exception as e:
            logger.error(f"Unexpected error getting history: {e}")
            return []

    def get_recent_messages_for_context(
        self, session_id: str, max_messages: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get recent messages formatted for LLM context.

        Uses LangChain's trim_messages to intelligently manage conversation window.

        Args:
            session_id: Unique session identifier
            max_messages: Maximum number of recent messages (defaults to config)

        Returns:
            List of {"role": str, "content": str} dictionaries
        """
        if not self.checkpointer:
            return []

        try:
            if max_messages is None:
                max_messages = settings.max_conversation_messages

            # Get all messages
            messages = self._get_messages_from_checkpoint(session_id)

            if not messages:
                return []

            # Use trim_messages to keep only recent messages
            # This ensures we maintain conversation coherence
            trimmed_messages = messages[-max_messages:] if len(messages) > max_messages else messages

            # Convert to simple dict format for LLM context
            return [
                {"role": "user" if isinstance(msg, HumanMessage) else "assistant",
                 "content": msg.content}
                for msg in trimmed_messages
            ]

        except Exception as e:
            logger.error(f"Unexpected error getting recent messages: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """
        Delete conversation history for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            True if successful, False otherwise
        """
        if not self.checkpointer or not self.graph:
            return False

        try:
            config = self._get_thread_config(session_id)

            # Check if session exists first
            messages = self._get_messages_from_checkpoint(session_id)

            if messages:
                # Save an empty state
                empty_state = ConversationState(messages=[])
                self.graph.invoke(empty_state, config)
                logger.info(f"🗑️  [CHECKPOINT] Deleted session {session_id[:8]}... (conversation history cleared)")
            else:
                logger.debug(f"[CHECKPOINT] Session {session_id[:8]}... not found (never existed)")

            return True

        except Exception as e:
            logger.error(f"Failed to delete session from checkpoint: {e}")
            return False

    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists in checkpoint.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session exists, False otherwise
        """
        if not self.checkpointer:
            return False

        try:
            messages = self._get_messages_from_checkpoint(session_id)
            return len(messages) > 0
        except Exception as e:
            logger.error(f"Failed to check session existence: {e}")
            return False

    def close(self):
        """Close checkpoint connection."""
        if self.checkpointer:
            try:
                # Close SQLite connection if it exists
                if hasattr(self, 'sqlite_conn') and self.sqlite_conn:
                    self.sqlite_conn.close()
                    logger.info("SQLite checkpoint connection closed")
                else:
                    logger.info("Checkpoint connection closed")
            except Exception as e:
                logger.error(f"Error closing checkpoint connection: {e}")
