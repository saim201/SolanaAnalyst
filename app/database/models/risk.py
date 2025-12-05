
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.config import Base


class RiskAssessment(Base):
    __tablename__ = 'risk_assessments'

    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to analysis
    analysis_id = Column(Integer, ForeignKey('agent_analyses.id'), nullable=False, index=True)
    
    # Trade details
    decision = Column(String(20), nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, nullable=False)
    action = Column(Float, nullable=False)
    
    # Market conditions
    current_price = Column(Float, nullable=False)
    atr = Column(Float, nullable=False)
    volatility_percent = Column(Float, nullable=False)
    
    # Portfolio status
    total_balance = Column(Float, nullable=False)
    cash_available = Column(Float, nullable=False)
    current_risk_percent = Column(Float, nullable=False)  # Current portfolio heat
    open_positions = Column(Integer, nullable=False)
    
    # Risk assessment
    approved = Column(String(20), nullable=False, index=True) 
    position_size_percent = Column(Float, nullable=False)  # % of portfolio to risk
    position_size_usd = Column(Float, nullable=False)
    max_loss_usd = Column(Float, nullable=False)
    
    # Suggested levels
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)
    
    # Risk factors
    risk_factors = Column(JSON, nullable=True)  # {volatility: 0-10, concentration: 0-10, etc}
    warnings = Column(JSON, nullable=True)  # Array of warning messages
    reasoning = Column(Text, nullable=False)
    
    # Confidence adjustment
    confidence_adjustment = Column(Float, nullable=False)  # -0.3 to 0.3
    final_confidence = Column(Float, nullable=False)  # Adjusted confidence
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_risk_analysis_id', 'analysis_id'),
        Index('idx_risk_approved', 'approved'),
        Index('idx_risk_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<RiskAssessment(decision={self.decision}, approved={self.approved}, position_size={self.position_size_percent}%)>"


class PortfolioHeat(Base):
    """Historical portfolio heat/risk tracking"""
    __tablename__ = 'portfolio_heat'

    id = Column(Integer, primary_key=True, index=True)
    
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    
    # Portfolio metrics
    total_balance = Column(Float, nullable=False)
    cash_available = Column(Float, nullable=False)
    sol_held = Column(Float, nullable=False)
    
    # Risk metrics
    current_heat_percent = Column(Float, nullable=False)  # % of portfolio at risk
    max_heat_percent = Column(Float, nullable=False)  # Maximum allowed (typically 2-3%)
    open_positions = Column(Integer, nullable=False)
    max_positions = Column(Integer, nullable=False)  # Typically 3-5
    
    # Volatility metrics
    portfolio_volatility = Column(Float, nullable=True)
    largest_position_percent = Column(Float, nullable=True)
    correlation_risk = Column(Float, nullable=True)  # Concentration risk
    
    # Recent performance
    win_rate_percent = Column(Float, nullable=True)
    consecutive_losses = Column(Integer, nullable=False, default=0)
    max_drawdown_percent = Column(Float, nullable=True)
    
    # Status
    can_trade = Column(String(20), nullable=False)  # YES, NO, RESTRICTED
    reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_heat_timestamp', 'timestamp'),
        Index('idx_heat_can_trade', 'can_trade'),
    )

    def __repr__(self):
        return f"<PortfolioHeat(timestamp={self.timestamp}, heat={self.current_heat_percent}%, can_trade={self.can_trade})>"
