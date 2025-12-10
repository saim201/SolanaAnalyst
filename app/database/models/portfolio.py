
from sqlalchemy import Column, Integer, Float, DateTime, Index
from datetime import datetime
from app.database.config import Base


class PortfolioState(Base):
    __tablename__ = 'portfolio_state'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True, unique=True)
    cash = Column(Float, nullable=False)
    sol_held = Column(Float, nullable=False)
    sol_price = Column(Float, nullable=False)
    net_worth = Column(Float, nullable=False)
    roi = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_portfolio_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<PortfolioState(timestamp={self.timestamp}, net_worth={self.net_worth}, roi={self.roi})>"
