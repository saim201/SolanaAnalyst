
from sqlalchemy import Column, Integer, Float, DateTime, BigInteger, Index
from sqlalchemy.sql import func
from app.database.config import Base


class CandlestickModel(Base):
    __tablename__ = 'candlestick_daily'

    id = Column(Integer, primary_key=True, index=True)
    open_time = Column(DateTime, nullable=False, unique=True, index=True)
    close_time = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    num_trades = Column(BigInteger, nullable=False)
    quote_volume = Column(BigInteger, nullable=False)
    taker_buy_base = Column(BigInteger, nullable=False)
    taker_buy_quote = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_candlestick_opentime', 'open_time'),
    )


class CandlestickIntradayModel(Base):
    __tablename__ = 'candlestick_intraday'

    id = Column(Integer, primary_key=True, index=True)
    open_time = Column(DateTime, nullable=False, unique=True, index=True)
    close_time = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    num_trades = Column(BigInteger, nullable=False)
    quote_volume = Column(BigInteger, nullable=False)
    taker_buy_base = Column(BigInteger, nullable=False)
    taker_buy_quote = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_candlestick_intraday_opentime', 'open_time'),
    )



class TickerModel(Base):
    __tablename__ = 'ticker_24h'

    id = Column(Integer, primary_key=True, index=True)
    lastPrice = Column(Float, nullable=False)
    priceChangePercent = Column(Float, nullable=False)
    openPrice = Column(Float, nullable=False)
    highPrice = Column(Float, nullable=False)
    lowPrice = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    quoteVolume = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)

    __table_args__ = (
        Index('idx_ticker24h_timestamp', 'timestamp'),
    )


class BTCTickerModel(Base):
    """Bitcoin ticker data for correlation analysis"""
    __tablename__ = 'btc_ticker_24h'

    id = Column(Integer, primary_key=True, index=True)
    lastPrice = Column(Float, nullable=False)
    priceChangePercent = Column(Float, nullable=False)
    openPrice = Column(Float, nullable=False)
    highPrice = Column(Float, nullable=False)
    lowPrice = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    quoteVolume = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)

    __table_args__ = (
        Index('idx_btc_ticker24h_timestamp', 'timestamp'),
    )


class BTCCandlestickModel(Base):
    """Bitcoin daily candles for correlation calculation"""
    __tablename__ = 'btc_candlestick_daily'

    id = Column(Integer, primary_key=True, index=True)
    open_time = Column(DateTime, nullable=False, unique=True, index=True)
    close_time = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    num_trades = Column(BigInteger, nullable=False)
    quote_volume = Column(BigInteger, nullable=False)
    taker_buy_base = Column(BigInteger, nullable=False)
    taker_buy_quote = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_btc_candlestick_opentime', 'open_time'),
    )