"""
Candlestick data models for daily and intraday price data.
"""
from sqlalchemy import Column, Integer, Float, DateTime, BigInteger, Index
from app.database.config import Base


class CandlestickData(Base):
    """Daily OHLCV candlestick data"""
    __tablename__ = 'candlestick_daily'

    id = Column(Integer, primary_key=True, index=True)
    open_time = Column(DateTime, nullable=False, unique=True, index=True)
    close_time = Column(DateTime, nullable=False, unique=True, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    num_trades = Column(BigInteger, nullable=False)
    quote_volume = Column(BigInteger, nullable=False)
    taker_buy_base = Column(BigInteger, nullable=False)
    taker_buy_quote = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('idx_candlestick_opentime', 'open_time'),
    )


class CandlestickIntradayModel(Base):
    """4-hour intraday candlestick data for entry timing"""
    __tablename__ = 'candlestick_intraday'

    id = Column(Integer, primary_key=True, index=True)
    open_time = Column(DateTime, nullable=False, unique=True, index=True)
    close_time = Column(DateTime, nullable=False, unique=True, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    num_trades = Column(BigInteger, nullable=False)
    quote_volume = Column(BigInteger, nullable=False)
    taker_buy_base = Column(BigInteger, nullable=False)
    taker_buy_quote = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('idx_candlestick_intraday_opentime', 'open_time'),
    )
