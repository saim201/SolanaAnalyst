"""
Data manager for saving fetched data to PostgreSQL
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict
from sqlalchemy.dialects.postgresql import insert
from .config import get_db_session
from .models import PriceData, TransactionData, NewsData


class DataManager:
    def __init__(self):
        self.db = get_db_session()

    def save_price_data(self, df: pd.DataFrame) -> int:
        print(f"💾 Saving {len(df)} price records to database...")

        records = []
        for _, row in df.iterrows():
            record = {
                'timestamp': row['timestamp'],
                'open': float(row['price']),
                'high': float(row['price']),
                'low': float(row['price']),
                'close': float(row['price']),
                'volume': int(row['volume']),
                'market_cap': int(row['market_cap']) if pd.notna(row.get('market_cap')) else None,
                'circulating_supply': int(row['circulating_supply']) if pd.notna(row.get('circulating_supply')) else None,
                'total_supply': int(row['total_supply']) if pd.notna(row.get('total_supply')) else None,
                'max_supply': int(row['max_supply']) if pd.notna(row.get('max_supply')) else None,
                'fdv': int(row['fdv']) if pd.notna(row.get('fdv')) else None,
                'price_change_24h': float(row['price_change_24h']) if pd.notna(row.get('price_change_24h')) else None,
            }
            records.append(record)

        stmt = insert(PriceData).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['timestamp'],
            set_={
                'open': stmt.excluded.open,
                'high': stmt.excluded.high,
                'low': stmt.excluded.low,
                'close': stmt.excluded.close,
                'volume': stmt.excluded.volume,
                'market_cap': stmt.excluded.market_cap,
                'circulating_supply': stmt.excluded.circulating_supply,
                'total_supply': stmt.excluded.total_supply,
                'max_supply': stmt.excluded.max_supply,
                'fdv': stmt.excluded.fdv,
                'price_change_24h': stmt.excluded.price_change_24h,
            }
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f"✅ Saved {len(records)} price records")
        return len(records)

    def save_transaction_data(self, df: pd.DataFrame) -> int:
        print(f"💾 Saving {len(df)} transaction records to database...")

        records = []
        for _, row in df.iterrows():
            record = {
                'day': row['day'],
                'transaction_count': int(row['transaction_count']),
                'unique_addresses': int(row['unique_addresses']),
                'gas_used': int(row['gas_used']),
            }
            records.append(record)

        stmt = insert(TransactionData).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['day'],
            set_={
                'transaction_count': stmt.excluded.transaction_count,
                'unique_addresses': stmt.excluded.unique_addresses,
                'gas_used': stmt.excluded.gas_used,
            }
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f"✅ Saved {len(records)} transaction records")
        return len(records)

    def save_news_data(self, articles: List[Dict]) -> int:
        print(f"💾 Saving {len(articles)} news articles to database...")

        records = []
        for article in articles:
            published_at = article['published_at']
            if isinstance(published_at, str):
                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))

            record = {
                'title': article['title'][:500],
                'url': article['url'][:1000],
                'source': article['source'][:200],
                'published_at': published_at,
                'content': article.get('content'),
                'sentiment': article.get('sentiment'),
            }
            records.append(record)

        stmt = insert(NewsData).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['url'],
            set_={
                'title': stmt.excluded.title,
                'source': stmt.excluded.source,
                'published_at': stmt.excluded.published_at,
                'content': stmt.excluded.content,
                'sentiment': stmt.excluded.sentiment,
            }
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f"✅ Saved {len(records)} news articles")
        return len(records)

    def get_latest_price_date(self):
        result = self.db.query(PriceData).order_by(PriceData.timestamp.desc()).first()
        return result.timestamp if result else None

    def get_latest_transaction_date(self):
        result = self.db.query(TransactionData).order_by(TransactionData.day.desc()).first()
        return result.day if result else None

    def get_latest_news_date(self):
        result = self.db.query(NewsData).order_by(NewsData.published_at.desc()).first()
        return result.published_at if result else None

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
