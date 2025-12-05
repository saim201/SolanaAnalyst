"""
Position tracking model for the Portfolio Management and Risk Management agents.
Tracks open positions with entry/exit prices, stop-loss, and take-profit levels.
"""
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, Index
from datetime import datetime
from app.database.config import Base


class Position(Base):
    """Open or closed trading position"""
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, index=True)
    
    # Position metadata
    status = Column(String(20), nullable=False, index=True)  # OPEN, CLOSED, CANCELED
    symbol = Column(String(20), nullable=False, index=True)  # e.g., SOL/USDT
    
    # Entry details
    entry_price = Column(Float, nullable=False)
    entry_date = Column(DateTime, nullable=False, index=True)
    entry_reason = Column(Text, nullable=True)  # Why we entered (analysis summary)
    
    # Position size
    quantity = Column(Float, nullable=False)
    position_size_usd = Column(Float, nullable=False)  # Entry value in USD
    position_size_percent = Column(Float, nullable=False)  # % of portfolio
    
    # Risk management
    stop_loss = Column(Float, nullable=False)
    stop_loss_percent = Column(Float, nullable=False)  # % below entry
    take_profit = Column(Float, nullable=False)
    take_profit_percent = Column(Float, nullable=False)  # % above entry
    risk_reward_ratio = Column(Float, nullable=False)
    max_loss_usd = Column(Float, nullable=False)  # Max allowed loss
    
    # Exit details
    exit_price = Column(Float, nullable=True)
    exit_date = Column(DateTime, nullable=True, index=True)
    exit_reason = Column(String(50), nullable=True)  # TAKE_PROFIT, STOP_LOSS, MANUAL, TIMEOUT
    exit_notes = Column(Text, nullable=True)
    
    # Performance
    profit_loss_usd = Column(Float, nullable=True)
    profit_loss_percent = Column(Float, nullable=True)
    return_percent = Column(Float, nullable=True)
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_position_status', 'status'),
        Index('idx_position_entry_date', 'entry_date'),
        Index('idx_position_exit_date', 'exit_date'),
        Index('idx_position_symbol', 'symbol'),
    )

    def __repr__(self):
        return f"<Position(symbol={self.symbol}, status={self.status}, entry={self.entry_price}, qty={self.quantity})>"
