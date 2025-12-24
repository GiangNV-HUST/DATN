# -*- coding: utf-8 -*-
import psycopg2
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config


def run_migration():
    sql_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "database",
        "add_technical_alerts.sql"
    )

    print(f"Reading SQL from: {sql_file}")

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    print("Connecting to database...")
    conn = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )

    cur = conn.cursor()

    print("Running migration...")
    try:
        cur.execute(sql)
        conn.commit()
        print("Migration completed successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False
    finally:
        cur.close()
        conn.close()

    return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
