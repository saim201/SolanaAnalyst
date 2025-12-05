"""
Agent analysis and trading decision models.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.config import Base


class AgentAnalysis(Base):
    """Output from all agents in a single analysis run"""
    __tablename__ = 'agent_analyses'

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(100), nullable=False, index=True, unique=True)
    technical_analysis = Column(Text, nullable=False)
    news_analysis = Column(Text, nullable=False)
    reflection_analysis = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to TradeDecision
    trade_decision = relationship(
        "TradeDecision",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_agent_run_id', 'run_id'),
        Index('idx_agent_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<AgentAnalysis(run_id={self.run_id}, timestamp={self.timestamp})>"


class TradeDecision(Base):
    """Final trading decision based on agent analyses"""
    __tablename__ = 'trade_decisions'

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(
        Integer,
        ForeignKey('agent_analyses.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    decision = Column(String(20), nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, nullable=False)  # 0-1
    action = Column(Float, nullable=False)  # -1 to 1
    reasoning = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to AgentAnalysis
    analysis = relationship("AgentAnalysis", back_populates="trade_decision")

    __table_args__ = (
        Index('idx_trade_analysis_id', 'analysis_id'),
        Index('idx_trade_timestamp', 'timestamp'),
        Index('idx_trade_decision', 'decision'),
    )

    def __repr__(self):
        return f"<TradeDecision(analysis_id={self.analysis_id}, decision={self.decision}, confidence={self.confidence})>"
