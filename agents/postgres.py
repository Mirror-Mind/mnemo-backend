import os

from langgraph.checkpoint.memory import InMemorySaver

from helpers.db_utils import get_connection_pool
from models.resilient_postgres_saver import ResilientPostgresSaver


def get_checkpointer():
    """Get a PostgresSaver instance for workflow checkpointing."""
    db_url = os.getenv("DATABASE_URL")
    print(f"DEBUG: DATABASE_URL = {db_url}")
    if not db_url:
        # Return an in-memory checkpointer for development/testing
        print("DEBUG: Using InMemorySaver")
        return InMemorySaver()

    print("DEBUG: Using ResilientPostgresSaver")
    connection_pool = get_connection_pool(db_url)
    checkpointer = ResilientPostgresSaver(connection_pool)
    checkpointer.setup()
    return checkpointer
