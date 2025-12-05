
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from datetime import datetime
from app.database.config import Base


class NewsData(Base):
    __tablename__ = 'news_data'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    source = Column(String(200), nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    content = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)  # CRITICAL, HIGH, MEDIUM
    priority = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_news_published', 'published_at'),
        Index('idx_news_sentiment', 'sentiment'),
        Index('idx_news_priority', 'priority'),
    )

    def __repr__(self):
        return f"<NewsData(title={self.title[:50]}, sentiment={self.sentiment})>"
