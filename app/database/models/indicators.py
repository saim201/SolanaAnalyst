from sqlalchemy import Column, Integer, Float, DateTime, String, Index
from datetime import datetime
from app.database.config import Base


class IndicatorsData(Base):
    __tablename__ = 'indicators'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)

    ema20 = Column(Float, nullable=True)
    ema50 = Column(Float, nullable=True)
    ema200 = Column(Float, nullable=True)  # Major trend bias indicator

    # MACD
    macd_line = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_histogram = Column(Float, nullable=True)

    # Momentum
    rsi14 = Column(Float, nullable=True)
    rsi_divergence_type = Column(String(20), nullable=True)  
    rsi_divergence_strength = Column(Float, nullable=True)   

    # Volatility 
    bb_upper = Column(Float, nullable=True)
    bb_lower = Column(Float, nullable=True)
    atr = Column(Float, nullable=True)

    # Volume
    volume_ma20 = Column(Float, nullable=True)
    volume_current = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)

    # Support/Resistance 
    support1 = Column(Float, nullable=True)
    support1_percent = Column(Float, nullable=True)
    support2 = Column(Float, nullable=True)
    support2_percent = Column(Float, nullable=True)

    resistance1 = Column(Float, nullable=True)
    resistance1_percent = Column(Float, nullable=True)
    resistance2 = Column(Float, nullable=True)
    resistance2_percent = Column(Float, nullable=True)

    # Fibonacci Retracement 
    fib_level_382 = Column(Float, nullable=True)
    fib_level_618 = Column(Float, nullable=True)

    # Pivot Point (MODIFIED: Keep weekly pivot for market bias, remove daily S/R levels)
    pivot_weekly = Column(Float, nullable=True)  # Weekly pivot for bias (not daily)

    # 24h Ticker Indicators
    momentum_24h = Column(Float, nullable=True)
    range_position_24h = Column(Float, nullable=True)
    volume_surge_24h = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_indicators_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<IndicatorsData(timestamp={self.timestamp}, rsi14={self.rsi14}, ema20={self.ema20})>"


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
