#!/usr/bin/env python3
"""
Setup script for PGVector extension and test database memory integration.
"""

import os
import sys
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.workflows.whatsapp.memory import WhatsAppMemoryManager


def setup_pgvector_extension():
    """Set up the PGVector extension in the PostgreSQL database."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("Please set your DATABASE_URL in the format:")
        print("postgresql://username:password@localhost:5432/database_name")
        return False

    try:
        print(f"🔗 Connecting to database: {database_url}")

        # Parse the database URL
        parsed = urlparse(database_url)

        # Connect to the database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("✅ Connected to PostgreSQL database")

        # Check if pgvector extension exists
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
        extension_exists = cursor.fetchone()

        if extension_exists:
            print("✅ PGVector extension is already installed")
        else:
            print("📦 Installing PGVector extension...")
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                print("✅ PGVector extension installed successfully")
            except psycopg2.Error as e:
                print(f"❌ Failed to install PGVector extension: {e}")
                print(
                    "💡 You may need to install pgvector on your PostgreSQL server first:"
                )
                print("   - For macOS with Homebrew: brew install pgvector")
                print("   - For Ubuntu/Debian: apt-get install postgresql-15-pgvector")
                print(
                    "   - Or compile from source: https://github.com/pgvector/pgvector"
                )
                return False

        # Check database info
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"📊 PostgreSQL version: {version}")

        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        print(f"🗄️  Current database: {db_name}")

        cursor.close()
        conn.close()

        return True

    except psycopg2.Error as e:
        print(f"❌ Database connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_memory_with_database():
    """Test the memory manager with database persistence."""
    print("\n🧪 Testing memory manager with database persistence...")

    # Set environment to use PGVector
    os.environ["USE_PGVECTOR_MEM0"] = "true"
    os.environ["MEM0_COLLECTION_NAME"] = "whatsapp_bot_memories"

    try:
        # Initialize memory manager
        print("1. Initializing memory manager with PGVector...")
        memory_manager = WhatsAppMemoryManager()
        print("✅ Memory manager initialized")

        # Test adding a memory
        print("\n2. Adding test memory...")
        test_user_id = "whatsapp_user_123"
        test_content = "User prefers vegetarian food and lives in San Francisco"

        result = memory_manager.add_single_memory(
            content=test_content,
            user_id=test_user_id,
            metadata={"source": "whatsapp", "type": "preference"},
        )

        if result:
            print("✅ Memory added successfully to database")
        else:
            print("❌ Failed to add memory to database")
            return False

        # Wait a moment for indexing
        import time

        print("\n3. Waiting for database indexing...")
        time.sleep(2)

        # Test searching memory
        print("\n4. Searching for memories...")
        search_results = memory_manager.search_memories("vegetarian", test_user_id)

        if search_results:
            print(f"✅ Found {len(search_results)} memories in database:")
            for i, memory in enumerate(search_results, 1):
                print(f"   {i}. {memory.get('memory', 'N/A')}")
        else:
            print("⚠️  No memories found in search")

        print("\n🎉 Database memory test completed!")
        return True

    except Exception as e:
        print(f"❌ Error testing memory with database: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_database_tables():
    """Check what tables were created in the database."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not found")
        return

    try:
        print("\n📋 Checking database tables...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # List all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()

        if tables:
            print("📊 Tables in database:")
            for table in tables:
                table_name = table[0]
                print(f"   - {table_name}")

                # Check if it's a memory-related table
                if "memory" in table_name.lower() or "vector" in table_name.lower():
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    count = cursor.fetchone()[0]
                    print(f"     └── {count} records")
        else:
            print("📭 No tables found in database")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error checking database tables: {e}")


def main():
    """Main setup and test function."""
    print("🚀 Setting up PGVector for WhatsApp Bot Memory\n")

    # Step 1: Setup PGVector extension
    if not setup_pgvector_extension():
        print("\n❌ Failed to setup PGVector extension")
        return False

    # Step 2: Test memory with database
    if not test_memory_with_database():
        print("\n❌ Failed to test memory with database")
        return False

    # Step 3: Check what tables were created
    check_database_tables()

    print("\n✅ Setup completed successfully!")
    print("\n💡 Your WhatsApp bot memory is now using PostgreSQL with PGVector!")
    print("   - Memories will persist across restarts")
    print("   - You can query the database to see stored memories")
    print("   - Tables are automatically created by Mem0")

    return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
