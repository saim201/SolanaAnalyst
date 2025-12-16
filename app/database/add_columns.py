import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from .config import engine
from sqlalchemy import text


def add_columns():    
    # (table_name, column_name, column_type)
    columns_to_add = [
        ("news_analyst", "all_recent_news", "JSON"),
    ]
    
    with engine.connect() as conn:
        for table_name, column_name, column_type in columns_to_add:
            try:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                conn.execute(text(sql))
                print(f"✓ Added {column_name} to {table_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"- {column_name} already exists in {table_name}, skipping")
                else:
                    print(f"✗ Error adding {column_name} to {table_name}: {e}")
        
        conn.commit()
        

if __name__ == "__main__":
    add_columns()