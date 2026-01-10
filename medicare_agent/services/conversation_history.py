"""Conversation history management using Redis."""

import json
import logging
from typing import List, Dict, Any, Optional
import redis
from redis.exceptions import RedisError

from medicare_agent.config import settings

logger = logging.getLogger(__name__)


class ConversationHistoryService:
    """Manages conversation history storage and retrieval using Redis."""

    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password if settings.redis_password else None,
                db=settings.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            self.redis_client.ping()
            logger.info(
                f"✓ Redis connection established: {settings.redis_host}:{settings.redis_port} (db={settings.redis_db})"
            )
            logger.info(f"✓ Conversation history persistence: ENABLED (TTL={settings.conversation_history_ttl}s, max_messages={settings.max_conversation_messages})")
        except RedisError as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            logger.warning("⚠ Conversation history will NOT be persisted - running in stateless mode")
            self.redis_client = None

    def _get_key(self, session_id: str) -> str:
        """Generate Redis key for a session."""
        return f"conversation:{session_id}"

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
        if not self.redis_client:
            return False

        try:
            key = self._get_key(session_id)
            message = {
                "role": role,
                "content": content,
            }
            if metadata:
                message["metadata"] = metadata

            # Get current history
            history = self.get_history(session_id, limit=None)
            history.append(message)

            # Keep only recent messages to limit memory usage
            if len(history) > settings.max_conversation_messages * 2:
                # Keep last N turns (N user + N assistant messages)
                history = history[-(settings.max_conversation_messages * 2):]

            # Save to Redis
            self.redis_client.setex(
                key,
                settings.conversation_history_ttl,
                json.dumps(history, ensure_ascii=False)
            )
            logger.info(
                f"📝 [REDIS] Saved {role} message to session {session_id[:8]}... "
                f"(total: {len(history)} messages, {len(content[:100])}... chars)"
            )
            return True

        except RedisError as e:
            logger.error(f"Failed to add message to Redis: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error adding message: {e}")
            return False

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
        if not self.redis_client:
            return []

        try:
            key = self._get_key(session_id)
            data = self.redis_client.get(key)

            if not data:
                return []

            history = json.loads(data)

            # Apply limit if specified
            if limit is not None and limit > 0:
                history = history[-limit:]

            if history:
                logger.info(f"📖 [REDIS] Retrieved {len(history)} messages for session {session_id[:8]}...")
            return history

        except RedisError as e:
            logger.error(f"Failed to get history from Redis: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode history JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting history: {e}")
            return []

    def get_recent_messages_for_context(
        self, session_id: str, max_messages: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get recent messages formatted for LLM context.

        Args:
            session_id: Unique session identifier
            max_messages: Maximum number of recent messages (defaults to config)

        Returns:
            List of {"role": str, "content": str} dictionaries
        """
        if max_messages is None:
            max_messages = settings.max_conversation_messages

        history = self.get_history(session_id, limit=max_messages)

        # Return only role and content for LLM context
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ]

    def delete_session(self, session_id: str) -> bool:
        """
        Delete conversation history for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            key = self._get_key(session_id)
            deleted = self.redis_client.delete(key)
            if deleted > 0:
                logger.info(f"🗑️  [REDIS] Deleted session {session_id[:8]}... (conversation history cleared)")
            else:
                logger.debug(f"[REDIS] Session {session_id[:8]}... not found (already expired or never existed)")
            return True

        except RedisError as e:
            logger.error(f"Failed to delete session from Redis: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting session: {e}")
            return False

    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists in Redis.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session exists, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            key = self._get_key(session_id)
            return self.redis_client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Failed to check session existence: {e}")
            return False

    def refresh_ttl(self, session_id: str) -> bool:
        """
        Refresh TTL for a session (extend expiration time).

        Args:
            session_id: Unique session identifier

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            key = self._get_key(session_id)
            if self.redis_client.exists(key):
                self.redis_client.expire(key, settings.conversation_history_ttl)
                logger.debug(f"Refreshed TTL for session {session_id}")
                return True
            return False
        except RedisError as e:
            logger.error(f"Failed to refresh TTL: {e}")
            return False

    def close(self):
        """Close Redis connection."""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
