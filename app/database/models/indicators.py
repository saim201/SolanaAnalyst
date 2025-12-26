from sqlalchemy import Column, Integer, Float, DateTime, String, Index
from datetime import datetime
from app.database.config import Base


class IndicatorsModel(Base):
    __tablename__ = 'indicators'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)

    ema20 = Column(Float, nullable=True)
    ema50 = Column(Float, nullable=True)
    ema200 = Column(Float, nullable=True)  # Major trend bias indicator

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

    volume_ma20 = Column(Float, nullable=True)
    volume_current = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    volume_classification = Column(String(20), nullable=True)  # STRONG/ACCEPTABLE/WEAK/DEAD
    volume_trading_allowed = Column(String(10), nullable=True)  # True/False as string
    volume_confidence_multiplier = Column(Float, nullable=True)  # 0.0-1.0
    days_since_volume_spike = Column(Integer, nullable=True)  # Days since last >1.5x spike

    # Ichimoku & 14-day levels
    kijun_sen = Column(Float, nullable=True)  # Ichimoku baseline
    high_14d = Column(Float, nullable=True)  # 14-day high
    low_14d = Column(Float, nullable=True)  # 14-day low

    # Additional momentum
    stoch_rsi = Column(Float, nullable=True)  # Stochastic RSI (0-1)
    atr_percent = Column(Float, nullable=True)  # ATR as % of price

    support1 = Column(Float, nullable=True)
    support1_percent = Column(Float, nullable=True)
    support2 = Column(Float, nullable=True)
    support2_percent = Column(Float, nullable=True)

    resistance1 = Column(Float, nullable=True)
    resistance1_percent = Column(Float, nullable=True)
    resistance2 = Column(Float, nullable=True)
    resistance2_percent = Column(Float, nullable=True)

    fib_level_382 = Column(Float, nullable=True)
    fib_level_618 = Column(Float, nullable=True)

    pivot_weekly = Column(Float, nullable=True) 

    momentum_24h = Column(Float, nullable=True)
    range_position_24h = Column(Float, nullable=True)
    volume_surge_24h = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_indicators_timestamp', 'timestamp'),
    )



