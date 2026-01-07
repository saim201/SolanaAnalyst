import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from app.database.config import DATABASE_URL
from datetime import datetime


def run_migration():
    print(f"Starting migration at {datetime.now()}")
    print(f"Connecting to: {DATABASE_URL}")

    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE technical_analyst ALTER COLUMN thinking TYPE TEXT"))
            conn.commit()
            print("Changed 'thinking' from JSON to TEXT in technical_analyst")

            conn.execute(text("ALTER TABLE trader_analyst ALTER COLUMN confidence TYPE JSON USING json_build_object('score', confidence, 'reasoning', '')"))
            conn.commit()
            print("Changed 'confidence' from Float to JSON in trader_analyst")

        print(f"\n✅ Migration completed successfully at {datetime.now()}")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    run_migration()
