"""
CFGI (Fear & Greed Index) data model for caching API responses.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from datetime import datetime
from app.database.config import Base


class CFGIData(Base):
    """Stores CFGI Fear & Greed Index data for caching."""
    __tablename__ = 'cfgi_data'

    id = Column(Integer, primary_key=True, index=True)
    score = Column(Float, nullable=False)
    classification = Column(String(20), nullable=False)
    social = Column(Float, nullable=True)
    whales = Column(Float, nullable=True)
    trends = Column(Float, nullable=True)
    sol_price = Column(Float, nullable=True)
    cfgi_timestamp = Column(DateTime, nullable=False)
    fetched_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_cfgi_fetched_at', 'fetched_at'),
    )

    def __repr__(self):
        return f"<CFGIData(score={self.score}, classification='{self.classification}')>"

    def to_dict(self):
        return {
            "score": self.score,
            "classification": self.classification,
            "social": self.social,
            "whales": self.whales,
            "trends": self.trends,
            "sol_price": self.sol_price,
            "cfgi_timestamp": self.cfgi_timestamp.isoformat() if self.cfgi_timestamp else None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None
        }
