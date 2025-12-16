from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON, Index, ForeignKey
from datetime import datetime
from app.database.config import Base


class TechnicalAnalyst(Base):
    __tablename__ = 'technical_analyst'

    id = Column(Integer, primary_key=True, index=True)    
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
        Index('idx_technical_created_at', 'created_at'),
        Index('idx_technical_recommendation', 'recommendation'),
    )


class NewsAnalyst(Base):
    __tablename__ = 'news_analyst'

    id = Column(Integer, primary_key=True, index=True)    
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
        # Index('idx_news_timestamp', 'timestamp'),
        Index('idx_news_stance', 'stance'),
    )



class ReflectionAnalyst(Base):
    __tablename__ = 'reflection_analyst'

    id = Column(Integer, primary_key=True, index=True)
    bull_case_summary = Column(Text, nullable=True)
    bear_case_summary = Column(Text, nullable=True)
    bull_strength = Column(Float, nullable=False)
    bear_strength = Column(Float, nullable=False)
    recommendation = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    primary_risk = Column(Text, nullable=True)
    monitoring_trigger = Column(Text, nullable=True)
    consensus_points = Column(JSON, nullable=True)
    conflict_points = Column(JSON, nullable=True)
    blind_spots = Column(JSON, nullable=True)
    reasoning = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Index('idx_reflection_timestamp', 'timestamp'),
        Index('idx_reflection_recommendation', 'recommendation'),
    )




class RiskAnalyst(Base):
    __tablename__ = 'risk_analyst'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    approved = Column(String(20), nullable=False, index=True)  # YES/NO
    
    position_size_percent = Column(Float, nullable=False)
    position_size_usd = Column(Float, nullable=False)
    max_loss_usd = Column(Float, nullable=False)
    
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)
    
    validation_details = Column(JSON, nullable=True)  # Which gates passed/failed
    warnings = Column(JSON, nullable=True)
    reasoning = Column(Text, nullable=False)
    
    total_balance = Column(Float, nullable=True)
    current_risk_percent = Column(Float, nullable=True)
    open_positions = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_risk_timestamp', 'timestamp'),
        Index('idx_risk_approved', 'approved'),
    )




class TraderAnalyst(Base):
    __tablename__ = 'trader_analyst'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    decision = Column(String(20), nullable=False, index=True)  # BUY/SELL/HOLD
    confidence = Column(Float, nullable=False)
    consensus_level = Column(String(20), nullable=True)
    
    agreeing_agents = Column(JSON, nullable=True)
    disagreeing_agents = Column(JSON, nullable=True)
    primary_concern = Column(Text, nullable=True)
    
    reasoning = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_trader_timestamp', 'timestamp'),
        Index('idx_trader_decision', 'decision'),
    )