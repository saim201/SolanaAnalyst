from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON, Index, ForeignKey
from datetime import datetime, timezone
from app.database.config import Base


class TechnicalAnalyst(Base):
    __tablename__ = 'technical_analyst'

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Core fields
    timestamp = Column(String(50))  # ISO format timestamp string
    recommendation = Column(String(10))  # BUY, SELL, HOLD, WAIT
    confidence = Column(Float)
    market_condition = Column(String(20))  # TRENDING, RANGING, VOLATILE, QUIET

    # New structured fields (store as JSON)
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
    confidence = Column(Float, nullable=False)

    # CFGI data
    cfgi_score = Column(Float, nullable=True)
    cfgi_classification = Column(String(20), nullable=True)
    cfgi_social = Column(Float, nullable=True)
    cfgi_whales = Column(Float, nullable=True)
    cfgi_trends = Column(Float, nullable=True)
    cfgi_interpretation = Column(Text, nullable=True)

    # News sentiment (migrated from old NewsAnalyst)
    news_sentiment_score = Column(Float, nullable=True)  # was overall_sentiment
    news_sentiment_label = Column(String(30), nullable=True)  # was sentiment_label
    news_catalysts_count = Column(Integer, nullable=True)
    news_risks_count = Column(Integer, nullable=True)

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
            "confidence": self.confidence,
            "market_fear_greed": {
                "score": self.cfgi_score,
                "classification": self.cfgi_classification,
                "social": self.cfgi_social,
                "whales": self.cfgi_whales,
                "trends": self.cfgi_trends,
                "interpretation": self.cfgi_interpretation
            },
            "news_sentiment": {
                "score": self.news_sentiment_score,
                "label": self.news_sentiment_label,
                "catalysts_count": self.news_catalysts_count,
                "risks_count": self.news_risks_count
            },
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