"""
SQLAlchemy models for CryptoTrade database
"""
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, BigInteger, Index
from datetime import datetime
from .config import Base


class PriceData(Base):
    __tablename__ = 'price_data'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    market_cap = Column(BigInteger, nullable=True)
    circulating_supply = Column(BigInteger, nullable=True)
    total_supply = Column(BigInteger, nullable=True)
    max_supply = Column(BigInteger, nullable=True)
    fdv = Column(BigInteger, nullable=True)
    price_change_24h = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_price_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<PriceData(timestamp={self.timestamp}, close={self.close})>"


class TransactionData(Base):
    __tablename__ = 'transaction_data'

    id = Column(Integer, primary_key=True, index=True)
    day = Column(DateTime, nullable=False, unique=True, index=True)
    transaction_count = Column(BigInteger, nullable=False)
    unique_addresses = Column(BigInteger, nullable=False)
    gas_used = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_txn_day', 'day'),
    )

    def __repr__(self):
        return f"<TransactionData(day={self.day}, txn_count={self.transaction_count})>"


class NewsData(Base):
    __tablename__ = 'news_data'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    source = Column(String(200), nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    content = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_news_published', 'published_at'),
        Index('idx_news_sentiment', 'sentiment'),
    )

    def __repr__(self):
        return f"<NewsData(title={self.title[:50]}, sentiment={self.sentiment})>"
