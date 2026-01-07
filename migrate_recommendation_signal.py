#!/usr/bin/env python3
"""
Migration script to rename 'recommendation' to 'recommendation_signal'
Run this ONCE to update existing database tables.

Usage: python migrate_recommendation_signal.py
"""

from sqlalchemy import create_engine, text, inspect
from app.database.config import DATABASE_URL

def migrate_database():
    """Migrate recommendation column to recommendation_signal"""

    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)

    with engine.connect() as conn:
        print("🔧 Starting database migration...\n")

        # 1. Migrate technical_analyst table
        if 'technical_analyst' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('technical_analyst')]

            if 'recommendation' in columns and 'recommendation_signal' not in columns:
                print("✅ Migrating technical_analyst table...")
                conn.execute(text("""
                    ALTER TABLE technical_analyst
                    RENAME COLUMN recommendation TO recommendation_signal
                """))
                conn.commit()
                print("   ✓ Renamed 'recommendation' → 'recommendation_signal'\n")
            elif 'recommendation_signal' in columns:
                print("⏭️  technical_analyst already has 'recommendation_signal'\n")
            else:
                print("⚠️  technical_analyst: No 'recommendation' column found\n")

        # 2. Migrate sentiment_analyst table (add column if missing)
        if 'sentiment_analyst' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('sentiment_analyst')]

            if 'recommendation_signal' not in columns:
                print("✅ Adding recommendation_signal to sentiment_analyst table...")
                conn.execute(text("""
                    ALTER TABLE sentiment_analyst
                    ADD COLUMN recommendation_signal VARCHAR(10)
                """))
                conn.commit()
                print("   ✓ Added 'recommendation_signal' column\n")
            else:
                print("⏭️  sentiment_analyst already has 'recommendation_signal'\n")

        # 3. Migrate reflection_analyst table
        if 'reflection_analyst' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('reflection_analyst')]

            if 'recommendation' in columns and 'recommendation_signal' not in columns:
                print("✅ Migrating reflection_analyst table...")
                conn.execute(text("""
                    ALTER TABLE reflection_analyst
                    RENAME COLUMN recommendation TO recommendation_signal
                """))
                conn.commit()
                print("   ✓ Renamed 'recommendation' → 'recommendation_signal'\n")
            elif 'recommendation_signal' in columns:
                print("⏭️  reflection_analyst already has 'recommendation_signal'\n")
            else:
                print("⚠️  reflection_analyst: No 'recommendation' column found\n")

        # 4. Update indexes if needed
        print("✅ Updating indexes...")

        # Drop old indexes if they exist
        try:
            conn.execute(text("DROP INDEX IF EXISTS idx_technical_recommendation"))
            conn.execute(text("DROP INDEX IF EXISTS idx_reflection_recommendation"))
        except:
            pass

        # Create new indexes
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_technical_recommendation
                ON technical_analyst(recommendation_signal)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_reflection_recommendation
                ON reflection_analyst(recommendation_signal)
            """))
            conn.commit()
            print("   ✓ Indexes updated\n")
        except Exception as e:
            print(f"   ⚠️  Index update warning: {e}\n")

    print("✅ Migration completed successfully!")


if __name__ == "__main__":
    try:
        migrate_database()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        exit(1)
