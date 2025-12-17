from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON, Index, ForeignKey
from datetime import datetime, timezone
from app.database.config import Base


class TechnicalAnalyst(Base):
    __tablename__ = 'technical_analyst'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    recommendation = Column(String(20), nullable=False)  # BUY/SELL/HOLD
    confidence = Column(Float, nullable=False)
    confidence_breakdown = Column(JSON, nullable=True)
    timeframe = Column(String(50), nullable=True)
    entry_level = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    key_signals = Column(JSON, nullable=True)  
    reasoning = Column(Text, nullable=False)
    recommendation_summary = Column(Text, nullable=True)
    watch_list = Column(JSON, nullable=True)
    thinking = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_technical_timestamp', 'timestamp'),
        Index('idx_technical_recommendation', 'recommendation'),
    )


class NewsAnalyst(Base):
    __tablename__ = 'news_analyst'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))  
    overall_sentiment = Column(Float, nullable=False)  
    sentiment_label = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=False)
    all_recent_news = Column(JSON, nullable=True)
    key_events = Column(JSON, nullable=True)
    event_summary = Column(JSON, nullable=True)
    risk_flags = Column(JSON, nullable=True)
    stance = Column(String(500), nullable=True)
    suggested_timeframe = Column(String(50), nullable=True)
    recommendation_summary = Column(String(500), nullable=True)
    what_to_watch = Column(JSON, nullable=True)
    invalidation = Column(String(500), nullable=True)
    thinking = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_news_timestamp', 'timestamp'),
        Index('idx_news_stance', 'stance'),
    )



class ReflectionAnalyst(Base):
    __tablename__ = 'reflection_analyst'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))  
    recommendation = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    agreement_analysis = Column(JSON, nullable=True)
    blind_spots = Column(JSON, nullable=True)
    risk_assessment = Column(JSON, nullable=True)
    monitoring = Column(JSON, nullable=True)
    confidence_calculation = Column(JSON, nullable=True)
    reasoning = Column(Text, nullable=True)
    thinking = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_reflection_timestamp', 'timestamp'),
        Index('idx_reflection_recommendation', 'recommendation'),
    )




class TraderAnalyst(Base):
    __tablename__ = 'trader_analyst'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    decision = Column(String(20), nullable=False, index=True)  # BUY/SELL/HOLD
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)

    agent_synthesis = Column(JSON, nullable=True)
    execution_plan = Column(JSON, nullable=True)
    risk_management = Column(JSON, nullable=True)
    thinking = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_trader_timestamp', 'timestamp'),
        Index('idx_trader_decision', 'decision'),
    )