"""
Migration Script: Remove Old Columns from sentiment_analyst Table

This script removes deprecated columns from the sentiment_analyst table that were part
of the old NewsAnalyst schema and are no longer used by the new SentimentAgent.

OLD COLUMNS TO REMOVE:
- overall_sentiment (replaced by news_sentiment_score)
- sentiment_label (replaced by news_sentiment_label)
- all_recent_news (no longer stored in DB, fetched live)
- event_summary (replaced by key_events)
- stance (replaced by summary)
- recommendation_summary (replaced by summary)

NEW SCHEMA COLUMNS (already exist):
- signal, confidence (overall)
- cfgi_score, cfgi_classification, cfgi_social, cfgi_whales, cfgi_trends, cfgi_interpretation (CFGI data)
- news_sentiment_score, news_sentiment_label, news_catalysts_count, news_risks_count (news data)
- key_events, risk_flags, summary, what_to_watch, invalidation, suggested_timeframe (analysis)
- thinking, model_used (metadata)

Run this script from the backend directory:
    python migrate_sentiment_schema.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database.config import get_db_session
from sqlalchemy import text


def run_migration():
    """Execute the database migration to remove old columns."""

    db = get_db_session()

    print("=" * 60)
    print("SENTIMENT_ANALYST TABLE MIGRATION")
    print("=" * 60)
    print("\nThis will remove the following OLD columns:")
    print("  - overall_sentiment (NOT NULL)")
    print("  - sentiment_label")
    print("  - all_recent_news")
    print("  - event_summary")
    print("  - stance")
    print("  - recommendation_summary")
    print("\nThe new schema uses:")
    print("  - signal, confidence (overall)")
    print("  - cfgi_* columns (Fear & Greed data)")
    print("  - news_sentiment_* columns (news data)")
    print("  - key_events, summary, etc. (analysis)")
    print("=" * 60)

    response = input("\nProceed with migration? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ Migration cancelled")
        db.close()
        return False

    try:
        # Drop old columns
        migrations = [
            'ALTER TABLE sentiment_analyst DROP COLUMN IF EXISTS overall_sentiment;',
            'ALTER TABLE sentiment_analyst DROP COLUMN IF EXISTS sentiment_label;',
            'ALTER TABLE sentiment_analyst DROP COLUMN IF EXISTS all_recent_news;',
            'ALTER TABLE sentiment_analyst DROP COLUMN IF EXISTS event_summary;',
            'ALTER TABLE sentiment_analyst DROP COLUMN IF EXISTS stance;',
            'ALTER TABLE sentiment_analyst DROP COLUMN IF EXISTS recommendation_summary;'
        ]

        print("\n🔄 Executing migrations...")
        for sql in migrations:
            try:
                db.execute(text(sql))
                column_name = sql.split('DROP COLUMN IF EXISTS ')[1].rstrip(';')
                print(f"  ✅ Dropped column: {column_name}")
            except Exception as e:
                print(f"  ⚠️  {sql}")
                print(f"     Error: {e}")

        db.commit()
        print("\n✅ Database migration completed successfully!")
        print("\nNEXT STEPS:")
        print("1. Update code that references old columns (see MIGRATION_CHANGES.md)")
        print("2. Test the SentimentAgent: python -m app.agents.news")
        print("3. Test the full pipeline: python -m app.agents.pipeline")

        return True

    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
