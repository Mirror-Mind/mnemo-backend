from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()


def get_connection_pool(db_url: str):
    print(f"DEBUG: Creating connection pool for {db_url}")
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
        "application_name": "orbia",
    }

    conn_pool = ConnectionPool(
        conninfo=db_url,
        kwargs=connection_kwargs,
        min_size=1,
        max_size=4,
        max_idle=60 * 2,
        open=True,
    )
    return conn_pool
