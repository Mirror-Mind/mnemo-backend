#!/usr/bin/env python3
"""
Check the content of memory tables in the database.
"""

import os

import psycopg2


def check_memory_tables():
    """Check the content of memory tables."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not found")
        return

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print("🔍 Checking memory tables content...\n")

        # First, check table schemas to understand the structure
        print("📋 Table schemas:")
        for table_name in ["whatsapp_bot_memories", "orbia_whatsapp_memories"]:
            try:
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                if columns:
                    print(f"\n   {table_name}:")
                    for col in columns:
                        print(f"     - {col[0]}: {col[1]} (nullable: {col[2]})")
                else:
                    print(f"\n   {table_name}: Table not found")
            except Exception as e:
                print(f"   Error getting schema for {table_name}: {e}")

        print("\n" + "=" * 50)

        # Check whatsapp_bot_memories table content
        try:
            cursor.execute("SELECT COUNT(*) FROM whatsapp_bot_memories;")
            count = cursor.fetchone()[0]
            print(f"\n📊 whatsapp_bot_memories table: {count} records")

            if count > 0:
                # Get first few records to see the structure
                cursor.execute("SELECT * FROM whatsapp_bot_memories LIMIT 3;")
                records = cursor.fetchall()
                print("   Sample records:")
                for i, record in enumerate(records, 1):
                    print(f"   Record {i}: {record}")
        except Exception as e:
            print(f"   Error checking whatsapp_bot_memories: {e}")

        # Check orbia_whatsapp_memories table
        try:
            cursor.execute("SELECT COUNT(*) FROM orbia_whatsapp_memories;")
            count = cursor.fetchone()[0]
            print(f"\n📊 orbia_whatsapp_memories table: {count} records")

            if count > 0:
                # Get first few records to see the structure
                cursor.execute("SELECT * FROM orbia_whatsapp_memories LIMIT 3;")
                records = cursor.fetchall()
                print("   Sample records:")
                for i, record in enumerate(records, 1):
                    print(f"   Record {i}: {record}")
        except Exception as e:
            print(f"   Error checking orbia_whatsapp_memories: {e}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error connecting to database: {e}")


if __name__ == "__main__":
    check_memory_tables()
