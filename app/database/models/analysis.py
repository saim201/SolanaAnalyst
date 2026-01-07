from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON, Index, ForeignKey
from datetime import datetime, timezone
from app.database.config import Base


class TechnicalAnalyst(Base):
    __tablename__ = 'technical_analyst'

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    timestamp = Column(String(50))
    recommendation_signal = Column(String(10))
    confidence = Column(JSON)
    market_condition = Column(String(20))
    thinking = Column(Text)
    analysis = Column(JSON)
    trade_setup = Column(JSON)
    action_plan = Column(JSON)
    watch_list = Column(JSON)
    invalidation = Column(JSON)
    confidence_reasoning = Column(JSON)

    __table_args__ = (
        Index('idx_technical_timestamp', 'timestamp'),
        Index('idx_technical_recommendation', 'recommendation_signal'),
    )


class SentimentAnalyst(Base):
    __tablename__ = 'sentiment_analyst'

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    timestamp = Column(String(50))
    recommendation_signal = Column(String(10))
    market_condition = Column(String(20))
    confidence = Column(JSON)
    market_fear_greed = Column(JSON)
    news_sentiment = Column(JSON)
    combined_sentiment = Column(JSON)
    positive_catalysts = Column(Integer)
    negative_risks = Column(Integer)
    key_events = Column(JSON)
    risk_flags = Column(JSON)
    what_to_watch = Column(JSON)
    invalidation = Column(Text)
    suggested_timeframe = Column(String(20))
    thinking = Column(Text)

    __table_args__ = (
        Index('idx_sentiment_timestamp', 'timestamp'),
        Index('idx_sentiment_recommendation', 'recommendation_signal'),
    )


class ReflectionAnalyst(Base):
    __tablename__ = 'reflection_analyst'

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    timestamp = Column(String(50))
    recommendation_signal = Column(String(10))
    market_condition = Column(String(20))
    confidence = Column(JSON)
    agent_alignment = Column(JSON)
    blind_spots = Column(JSON)
    primary_risk = Column(Text)
    monitoring = Column(JSON)
    calculated_metrics = Column(JSON)
    final_reasoning = Column(Text)
    thinking = Column(Text)

    __table_args__ = (
        Index('idx_reflection_timestamp', 'timestamp'),
        Index('idx_reflection_recommendation', 'recommendation_signal'),
    )


class TraderAnalyst(Base):
    __tablename__ = 'trader_analyst'

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    timestamp = Column(String(50))
    recommendation_signal = Column(String(10))
    market_condition = Column(String(50))
    confidence = Column(JSON)
    final_verdict = Column(JSON)
    trade_setup = Column(JSON)
    action_plan = Column(JSON)
    what_to_monitor = Column(JSON)
    risk_assessment = Column(JSON)
    thinking = Column(Text)

    __table_args__ = (
        Index('idx_trader_timestamp', 'timestamp'),
        Index('idx_trader_recommendation', 'recommendation_signal'),
    )
