"""
Initialize database with all tables
Runs all SQL scripts in database folder
"""
import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Database config
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5434'),
    'database': os.getenv('DB_NAME', 'stock'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres123')
}

# SQL files to run in order
sql_files = [
    'init.sql',  # Main schema
    'migration_alert_table.sql',  # Alert table migration
    'migration_subscribe_table.sql',  # Subscribe table migration
    'add_technical_alerts.sql',  # Technical alerts
    'fix_ratio_fk.sql',  # Fix foreign keys
    'migration_hybrid_system.sql',  # Hybrid system tables
    'migration_query_cache.sql',  # Query cache
]

database_dir = Path(__file__).parent / 'database'

print("=" * 70)
print("DATABASE INITIALIZATION")
print("=" * 70)

print(f"\nDatabase: {db_config['database']} @ {db_config['host']}:{db_config['port']}")
print(f"User: {db_config['user']}")

try:
    # Connect to database
    print("\n1. Connecting to PostgreSQL...")
    conn = psycopg2.connect(**db_config)
    conn.autocommit = False  # Use transactions
    cursor = conn.cursor()
    print("   Connected successfully!")

    # Drop existing schema if user confirms
    print("\n2. Cleaning up existing schema...")
    try:
        cursor.execute("DROP SCHEMA IF EXISTS stock CASCADE;")
        conn.commit()
        print("   Dropped existing 'stock' schema")
    except Exception as e:
        print(f"   Warning: {e}")
        conn.rollback()

    # Create TimescaleDB extension
    print("\n3. Creating TimescaleDB extension...")
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        conn.commit()
        print("   TimescaleDB extension ready")
    except Exception as e:
        print(f"   Warning: Could not create TimescaleDB extension: {e}")
        print("   Continuing with regular PostgreSQL...")
        conn.rollback()

    # Run SQL files
    print("\n4. Running SQL migration files...")

    for sql_file in sql_files:
        file_path = database_dir / sql_file

        if not file_path.exists():
            print(f"   [SKIP] {sql_file} - file not found")
            continue

        print(f"\n   Running {sql_file}...")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Execute SQL
            cursor.execute(sql_content)
            conn.commit()

            print(f"   [OK] {sql_file} executed successfully")

        except Exception as e:
            error_msg = str(e)

            # Check if error is ignorable
            if "already exists" in error_msg.lower():
                print(f"   [WARN] {sql_file} - objects already exist (continuing)")
                conn.rollback()
            elif "does not exist" in error_msg.lower() and "timescale" in error_msg.lower():
                print(f"   [WARN] {sql_file} - TimescaleDB not available (continuing)")
                conn.rollback()
            else:
                print(f"   [ERROR] {sql_file}: {error_msg}")
                conn.rollback()
                # Continue with next file instead of stopping
                continue

    # Verify tables created
    print("\n5. Verifying tables...")
    cursor.execute("""
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname IN ('stock', 'public')
        ORDER BY schemaname, tablename;
    """)

    tables = cursor.fetchall()

    if tables:
        print(f"\n   [OK] Found {len(tables)} tables:")

        # Group by schema
        by_schema = {}
        for schema, table in tables:
            if schema not in by_schema:
                by_schema[schema] = []
            by_schema[schema].append(table)

        for schema, table_list in sorted(by_schema.items()):
            print(f"\n   Schema '{schema}':")
            for table in sorted(table_list):
                print(f"     - {table}")
    else:
        print("   [WARN] No tables found!")

    # Close connection
    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("DATABASE INITIALIZATION COMPLETED SUCCESSFULLY")
    print("=" * 70)

except psycopg2.Error as e:
    print(f"\n[ERROR] Database error: {e}")
    print("\n" + "=" * 70)
    print("DATABASE INITIALIZATION FAILED")
    print("=" * 70)

except Exception as e:
    print(f"\n[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
    print("\n" + "=" * 70)
    print("DATABASE INITIALIZATION FAILED")
    print("=" * 70)
