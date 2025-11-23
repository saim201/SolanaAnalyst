"""
Database initialization script
"""
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import init_db, test_connection

load_dotenv()


def main():
    print("=" * 80)
    print("🚀 INITIALIZING CRYPTOTRADE DATABASE")
    print("=" * 80)

    print("\n1️⃣  Testing database connection... ")
    if not test_connection():
        print("\n❌ Database connection failed!")
        print("\nMake sure:")
        print("  1. PostgreSQL is running")
        print("  2. Database 'cryptotrade' exists")
        print("  3. DATABASE_URL in .env is correct")
        print("\nTo create the database, run:")
        print("  createdb cryptotrade")
        print("  or")
        print("  psql -U postgres -c 'CREATE DATABASE cryptotrade;'")
        return

    print("\n2️⃣  Creating database tables...")
    try:
        init_db()
        print("\n" + "=" * 80)
        print("✅ DATABASE INITIALIZATION COMPLETE")
        print("=" * 80)
        print("\nTables created:")
        print("  - price_data")
        print("  - transaction_data")
        print("  - news_data")

    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")
        return


if __name__ == "__main__":
    main()
