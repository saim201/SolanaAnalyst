import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
SOLSCAN_API_KEY = os.getenv('SOLSCAN_API_KEY')

# Fallback to SQLite for testing if DATABASE_URL not set
if not DATABASE_URL:
    DATABASE_URL = 'sqlite:///:memory:'

Base = declarative_base()

if 'postgresql' in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False
    )
else:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e
