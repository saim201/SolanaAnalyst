from sqlalchemy import Column, Integer, Float, String, DateTime, Text, BigInteger, Index, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .config import Base



class CandlestickData(Base):
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


class IndicatorsData(Base):
    __tablename__ = 'indicators'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    
    # Trend Indicators
    ema20 = Column(Float, nullable=True)
    ema50 = Column(Float, nullable=True)
    ema200 = Column(Float, nullable=True)
    
    # MACD
    macd_line = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_histogram = Column(Float, nullable=True)
    
    # Momentum
    rsi14 = Column(Float, nullable=True)
    
    # Volatility
    bb_upper = Column(Float, nullable=True)
    bb_middle = Column(Float, nullable=True)
    bb_lower = Column(Float, nullable=True)
    bb_width = Column(Float, nullable=True)
    bb_position = Column(Float, nullable=True)
    
    atr = Column(Float, nullable=True)
    volatility_percent = Column(Float, nullable=True)
    
    # Volume
    volume_ma20 = Column(Float, nullable=True)
    volume_current = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    obv = Column(Float, nullable=True)  # On-Balance Volume
    buy_pressure_ratio = Column(Float, nullable=True)  
    
    # Support/Resistance
    support1 = Column(Float, nullable=True)
    support1_percent = Column(Float, nullable=True)
    support2 = Column(Float, nullable=True)
    support2_percent = Column(Float, nullable=True)
    support3 = Column(Float, nullable=True)
    support3_percent = Column(Float, nullable=True)
    
    resistance1 = Column(Float, nullable=True)
    resistance1_percent = Column(Float, nullable=True)
    resistance2 = Column(Float, nullable=True)
    resistance2_percent = Column(Float, nullable=True)
    resistance3 = Column(Float, nullable=True)
    resistance3_percent = Column(Float, nullable=True)
    
    # Fibonacci Retracement
    fib_level_0 = Column(Float, nullable=True)
    fib_level_236 = Column(Float, nullable=True)
    fib_level_382 = Column(Float, nullable=True)
    fib_level_500 = Column(Float, nullable=True)
    fib_level_618 = Column(Float, nullable=True)
    fib_level_786 = Column(Float, nullable=True)
    fib_level_100 = Column(Float, nullable=True)
    
    # Pivot Points (from previous day)
    pivot = Column(Float, nullable=True)
    pivot_s1 = Column(Float, nullable=True)
    pivot_s2 = Column(Float, nullable=True)
    pivot_r1 = Column(Float, nullable=True)
    pivot_r2 = Column(Float, nullable=True)

    # Intraday 4h Indicators (SECONDARY - entry timing)
    ema20_4h = Column(Float, nullable=True)
    ema50_4h = Column(Float, nullable=True)
    high_4h = Column(Float, nullable=True)
    low_4h = Column(Float, nullable=True)
    range_4h = Column(Float, nullable=True)
    price_from_low_4h = Column(Float, nullable=True)

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


class NewsData(Base):
    __tablename__ = 'news_data'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    source = Column(String(200), nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    content = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)
    priority = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_news_published', 'published_at'),
        Index('idx_news_sentiment', 'sentiment'),
        Index('idx_news_priority', 'priority'),
    )

    def __repr__(self):
        return f"<NewsData(title={self.title[:50]}, sentiment={self.sentiment})>"


class AgentAnalysis(Base):
    __tablename__ = 'agent_analyses'

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(100), nullable=False, index=True, unique=True)
    technical_analysis = Column(Text, nullable=False)
    news_analysis = Column(Text, nullable=False)
    reflection_analysis = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to TradeDecision
    trade_decision = relationship("TradeDecision", back_populates="analysis", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_agent_run_id', 'run_id'),
        Index('idx_agent_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<AgentAnalysis(run_id={self.run_id}, timestamp={self.timestamp})>"


class TradeDecision(Base):
    __tablename__ = 'trade_decisions'

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey('agent_analyses.id', ondelete='CASCADE'), nullable=False, index=True)
    decision = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    action = Column(Float, nullable=False)
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
