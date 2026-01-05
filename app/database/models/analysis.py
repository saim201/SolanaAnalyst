from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON, Index, ForeignKey
from datetime import datetime, timezone
from app.database.config import Base


class TechnicalAnalyst(Base):
    __tablename__ = 'technical_analyst'

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    timestamp = Column(String(50))  # Agents timestamp
    recommendation = Column(String(10))  # BUY, SELL, HOLD, WAIT
    confidence = Column(JSON)  #  {analysis_confidence, setup_quality, interpretation}
    market_condition = Column(String(20))  # TRENDING, RANGING, VOLATILE, QUIET

    summary = Column(Text)  # 2-3 sentence actionable summary
    thinking = Column(JSON)  # Array of reasoning steps
    analysis = Column(JSON)  # {trend, momentum, volume} objects
    trade_setup = Column(JSON)  # {viability, entry, stop_loss, take_profit, etc.}
    action_plan = Column(JSON)  # {primary, alternative, if_in_position, avoid}
    watch_list = Column(JSON)  # {next_24h, next_48h} arrays
    invalidation = Column(JSON)  # Array of invalidation conditions
    confidence_reasoning = Column(JSON)  # {supporting, concerns, assessment}

    __table_args__ = (
        Index('idx_technical_timestamp', 'timestamp'),
        Index('idx_technical_recommendation', 'recommendation'),
    )


class SentimentAnalyst(Base):
    """
    Sentiment Agent output - combines CFGI Fear & Greed + News analysis.
    """
    __tablename__ = 'sentiment_analyst'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Overall signal
    signal = Column(String(30), nullable=False)  # BULLISH, BEARISH, NEUTRAL
    confidence = Column(JSON, nullable=False)  # Nested object: {analysis_confidence, signal_strength, interpretation}

    # CFGI data - stored as nested JSON (single source of truth)
    market_fear_greed = Column(JSON, nullable=True)  # {score, classification, social, whales, trends, interpretation}

    # News sentiment - stored as nested JSON (single source of truth)
    news_sentiment = Column(JSON, nullable=True)  # {score, label, catalysts_count, risks_count}

    # Events and analysis
    key_events = Column(JSON, nullable=True)
    risk_flags = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    what_to_watch = Column(JSON, nullable=True)
    invalidation = Column(Text, nullable=True)
    suggested_timeframe = Column(String(20), nullable=True)

    # Metadata
    thinking = Column(Text, nullable=True)
    model_used = Column(String(50), default="claude-3-5-haiku-20241022")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_sentiment_timestamp', 'timestamp'),
        Index('idx_sentiment_signal', 'signal'),
    )

    def to_dict(self):
        return {
            "signal": self.signal,
            "confidence": self.confidence,  # Nested JSON object from DB
            "market_fear_greed": self.market_fear_greed,  # Nested JSON object from DB
            "news_sentiment": self.news_sentiment,  # Nested JSON object from DB
            "key_events": self.key_events or [],
            "risk_flags": self.risk_flags or [],
            "summary": self.summary,
            "what_to_watch": self.what_to_watch or [],
            "invalidation": self.invalidation,
            "suggested_timeframe": self.suggested_timeframe,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# Keep NewsAnalyst as an alias for backward compatibility
NewsAnalyst = SentimentAnalyst



class ReflectionAnalyst(Base):
    __tablename__ = 'reflection_analyst'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    recommendation = Column(String(20), nullable=False)
    confidence = Column(JSON, nullable=False)  # Nested object: {analysis_confidence, final_confidence, interpretation}
    agreement_analysis = Column(JSON, nullable=True)
    blind_spots = Column(JSON, nullable=True)
    risk_assessment = Column(JSON, nullable=True)
    monitoring = Column(JSON, nullable=True)
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