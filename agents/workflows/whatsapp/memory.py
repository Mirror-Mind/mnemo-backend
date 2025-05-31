"""
Memory management utilities for WhatsApp workflow using Mem0.

This module includes retry logic with exponential backoff to handle PostgreSQL
connection drops and improve database operation reliability.
"""

import os
import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from mem0 import Memory

from helpers.logger_config import logger


def retry_on_db_connection_error(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator to retry database operations with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    # Check for database connection errors
                    if any(error_phrase in error_msg for error_phrase in [
                        "server closed the connection unexpectedly",
                        "connection closed",
                        "operationalerror",
                        "database connection",
                        "connection timeout"
                    ]):
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(
                                f"Database connection error on attempt {attempt + 1}/{max_retries}, retrying in {delay}s",
                                data={"error": str(e), "delay": delay}
                            )
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(
                                f"Database connection failed after {max_retries} attempts",
                                data={"error": str(e)}
                            )
                    # Re-raise the exception if it's not a connection error or max retries reached
                    raise e
            return None
        return wrapper
    return decorator


class WhatsAppMemoryManager:
    """Memory manager for WhatsApp conversations using Mem0."""

    def __init__(self):
        """Initialize the memory manager with appropriate configuration."""
        self.memory = self._create_memory_instance()

    @retry_on_db_connection_error(max_retries=5, base_delay=2.0)
    def _create_memory_instance(self) -> Memory:
        """Create Mem0 memory instance with production-ready configuration."""
        is_production = os.getenv("NODE_ENV") == "production"
        use_redis = os.getenv("USE_REDIS_MEM0", "false").lower() == "true"
        use_pgvector = os.getenv("USE_PGVECTOR_MEM0", "false").lower() == "true"

        # Auto-detect PGVector if DATABASE_URL is available and no explicit choice is made
        if not use_redis and not use_pgvector and os.getenv("DATABASE_URL"):
            use_pgvector = True
            logger.info(
                "Auto-detected DATABASE_URL, enabling PGVector for persistent memory storage"
            )

        # Base embedder and LLM configuration
        base_config = {
            "embedder": {
                "provider": "openai",
                "config": {
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "model": "text-embedding-3-small",
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "model": "gpt-4.1-mini-2025-04-14",
                },
            },
        }

        if use_pgvector:
            logger.info("Using PGVector vector store for Mem0")
            # Parse DATABASE_URL if available, otherwise use individual components
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                # Parse DATABASE_URL into individual components
                from urllib.parse import urlparse

                parsed = urlparse(database_url)
                config = {
                    **base_config,
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "user": parsed.username or "postgres",
                            "password": parsed.password or "postgres",
                            "host": parsed.hostname or "localhost",
                            "port": parsed.port or 5432,
                            "dbname": parsed.path.lstrip("/")
                            if parsed.path
                            else "orbia_db",
                            "collection_name": os.getenv(
                                "MEM0_COLLECTION_NAME", "orbia_whatsapp_memories"
                            ),
                        },
                    },
                }
            else:
                # Fallback to individual components
                config = {
                    **base_config,
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "user": os.getenv("POSTGRES_USER", "postgres"),
                            "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
                            "host": os.getenv("POSTGRES_HOST", "localhost"),
                            "port": os.getenv("POSTGRES_PORT", "5432"),
                            "dbname": os.getenv("POSTGRES_DB", "mnemo_db"),
                            "collection_name": os.getenv(
                                "MEM0_COLLECTION_NAME", "orbia_whatsapp_memories"
                            ),
                        },
                    },
                }
        elif use_redis:
            logger.info("Using Redis vector store for Mem0")
            config = {
                **base_config,
                "vector_store": {
                    "provider": "redis",
                    "config": {
                        "collection_name": os.getenv(
                            "MEM0_COLLECTION_NAME", "orbia_whatsapp_memories"
                        ),
                        "embedding_model_dims": 1536,
                        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
                        **(
                            {"username": os.getenv("REDIS_USERNAME")}
                            if os.getenv("REDIS_USERNAME")
                            else {}
                        ),
                        **(
                            {"password": os.getenv("REDIS_PASSWORD")}
                            if os.getenv("REDIS_PASSWORD")
                            else {}
                        ),
                    },
                },
            }
        else:
            logger.info("Using FAISS in-memory vector store for Mem0")
            # Use FAISS for in-memory storage (Python compatible)
            config = {
                **base_config,
                "vector_store": {
                    "provider": "faiss",
                    "config": {
                        "collection_name": "whatsapp-memories",
                        "path": "/tmp/faiss_memories",  # Temporary directory for FAISS index
                        "distance_strategy": "cosine",
                    },
                },
            }

        return Memory.from_config(config)

    @retry_on_db_connection_error()
    def search_memories(
        self, query: str, user_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for relevant memories based on query."""
        try:
            logger.info(
                "Searching memories",
                data={"query": query, "user_id": user_id, "limit": limit},
            )
            results = self.memory.search(query, user_id=user_id, limit=limit)
            # Handle different return formats from Mem0
            if isinstance(results, dict):
                extracted = results.get("results", [])
                return extracted
            elif isinstance(results, list):
                return results
            elif hasattr(results, "results"):
                extracted = results.results
                return extracted

            return []
        except AttributeError as attr_error:
            if "'list' object has no attribute 'id'" in str(attr_error):
                logger.warning(
                    "Mem0 library bug detected during search (list object has no attribute 'id')",
                    data={"error": str(attr_error), "query": query},
                    user_id=user_id,
                )
                return []
            else:
                logger.error(
                    "AttributeError searching memories",
                    data={"error": str(attr_error)},
                    user_id=user_id,
                )
                return []
        except Exception as e:
            logger.error("Error searching memories", error=str(e), user_id=user_id)
            return []

    @retry_on_db_connection_error()
    def add_memory(
        self,
        messages: List[BaseMessage],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add conversation messages to memory."""
        try:
            # Convert LangChain messages to Mem0 format
            mem0_messages = []
            for msg in messages:
                mem0_messages.append(
                    {"role": self._get_mem0_role(msg), "content": str(msg.content)}
                )

            self.memory.add(mem0_messages, user_id=user_id, metadata=metadata or {})
            logger.info(
                "Successfully added memories",
                data={"user_id": user_id, "message_count": len(messages)},
            )
            return True
        except AttributeError as attr_error:
            if "'list' object has no attribute 'id'" in str(attr_error):
                logger.warning(
                    "Mem0 library bug detected during add_memory (list object has no attribute 'id')",
                    data={"error": str(attr_error)},
                    user_id=user_id,
                )
                return False
            else:
                logger.error(
                    "AttributeError adding memories",
                    data={"error": str(attr_error)},
                    user_id=user_id,
                )
                return False
        except Exception as e:
            logger.error("Error adding memories", error=str(e), user_id=user_id)
            return False

    @retry_on_db_connection_error()
    def add_single_memory(
        self, content: str, user_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a single memory entry."""
        try:
            self.memory.add(content, user_id=user_id, metadata=metadata or {})
            logger.info("Successfully added single memory", data={"user_id": user_id})
            return True
        except AttributeError as attr_error:
            if "'list' object has no attribute 'id'" in str(attr_error):
                logger.warning(
                    "Mem0 library bug detected during add_single_memory (list object has no attribute 'id')",
                    data={"error": str(attr_error)},
                    user_id=user_id,
                )
                return False
            else:
                logger.error(
                    "AttributeError adding single memory",
                    data={"error": str(attr_error)},
                    user_id=user_id,
                )
                return False
        except Exception as e:
            logger.error("Error adding single memory", error=str(e), user_id=user_id)
            return False

    @retry_on_db_connection_error()
    def get_all_memories(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all memories for a user."""
        try:
            results = self.memory.get_all(user_id=user_id, limit=limit)
            # Handle different return formats from Mem0
            if isinstance(results, dict):
                return results.get("results", [])
            elif isinstance(results, list):
                return results
            elif hasattr(results, "results"):
                return results.results
            return results if results else []
        except AttributeError as attr_error:
            # Handle specific Mem0 library bug where 'list' object has no attribute 'id'
            if "'list' object has no attribute 'id'" in str(attr_error):
                logger.warning(
                    "Mem0 library bug detected (list object has no attribute 'id'), using search fallback",
                    data={"error": str(attr_error)},
                    user_id=user_id,
                )
                return self._get_memories_via_search_fallback(user_id, limit)
            else:
                logger.error(
                    "AttributeError getting all memories",
                    data={"error": str(attr_error)},
                    user_id=user_id,
                )
                return self._get_memories_via_search_fallback(user_id, limit)
        except Exception as e:
            logger.error("Error getting all memories", error=str(e), user_id=user_id)
            return self._get_memories_via_search_fallback(user_id, limit)

    def _get_memories_via_search_fallback(
        self, user_id: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback method to get memories using search when get_all fails."""
        logger.info("Attempting fallback search to retrieve memories", user_id=user_id)

        # Try multiple broad search queries to capture different types of memories
        search_queries = [
            "user information preferences",
            "conversation history",
            "user details",
            "personal information",
            "user context",
        ]

        all_memories = []
        seen_ids = set()

        for query in search_queries:
            try:
                fallback_results = self.memory.search(
                    query, user_id=user_id, limit=limit
                )

                # Process results
                if isinstance(fallback_results, dict):
                    memories = fallback_results.get("results", [])
                elif isinstance(fallback_results, list):
                    memories = fallback_results
                else:
                    continue

                # Add unique memories (deduplicate by memory ID if available)
                for memory in memories:
                    memory_id = memory.get("id") if isinstance(memory, dict) else None
                    if memory_id and memory_id not in seen_ids:
                        all_memories.append(memory)
                        seen_ids.add(memory_id)
                    elif not memory_id:  # No ID available, add anyway
                        all_memories.append(memory)

                # Stop if we have enough memories
                if len(all_memories) >= limit:
                    break

            except Exception as fallback_error:
                logger.warning(
                    "Search query failed during fallback",
                    data={"query": query, "error": str(fallback_error)},
                    user_id=user_id,
                )
                continue

        if not all_memories:
            logger.error("All fallback search attempts failed", user_id=user_id)
        else:
            logger.info(
                "Successfully retrieved memories via fallback search",
                data={"count": len(all_memories)},
                user_id=user_id,
            )

        return all_memories[:limit]  # Return up to the requested limit

    @retry_on_db_connection_error()
    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """Delete a specific memory."""
        try:
            self.memory.delete(memory_id=memory_id)
            logger.info(
                "Successfully deleted memory",
                data={"memory_id": memory_id, "user_id": user_id},
            )
            return True
        except Exception as e:
            logger.error("Error deleting memory", error=str(e))
            return False

    @retry_on_db_connection_error()
    def update_memory(self, memory_id: str, new_content: str, user_id: str) -> bool:
        """Update an existing memory."""
        try:
            self.memory.update(memory_id=memory_id, data=new_content)
            logger.info(
                "Successfully updated memory",
                data={"memory_id": memory_id, "user_id": user_id},
            )
            return True
        except Exception as e:
            logger.error("Error updating memory", error=str(e))
            return False

    def _get_mem0_role(self, message: BaseMessage) -> str:
        """Convert LangChain message type to Mem0 role."""
        # Check the class name directly for more reliable type detection
        class_name = message.__class__.__name__
        if class_name == "HumanMessage" or getattr(message, "_type", None) == "human":
            return "user"
        elif class_name == "AIMessage" or getattr(message, "_type", None) == "ai":
            return "assistant"
        elif (
            class_name == "SystemMessage" or getattr(message, "_type", None) == "system"
        ):
            return "system"
        else:
            # Fallback to checking the type attribute
            msg_type = getattr(message, "_type", "human")
            if msg_type == "human":
                return "user"
            elif msg_type == "ai":
                return "assistant"
            elif msg_type == "system":
                return "system"
            else:
                return "user"  # Default fallback
