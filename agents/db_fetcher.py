import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import get_db_session
from database.models import NewsData, CandlestickData, IndicatorsData, TradeDecision, TickerModel, CandlestickIntradayModel


class DataQuery:
    def __init__(self):
        self.db = get_db_session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def get_news_data(self, days: int = 7) -> list:
        cutoff = datetime.now() - timedelta(days=days)
        news = self.db.query(NewsData).filter(
            NewsData.published_at >= cutoff
        ).order_by(NewsData.priority, NewsData.published_at.desc()).all()

        if not news:
            return []

        # Convert to clean dict list
        news_data = []
        for article in news:
            news_data.append({
                'title': article.title,
                'source': article.source,
                'published_at': article.published_at.isoformat(),
                'priority': article.priority,
                'content': article.content[:300] if article.content else ""
            })

        return news_data



    def get_ticker_data(self) -> dict:
        ticker = self.db.query(TickerModel).order_by(
            TickerModel.timestamp.desc()
        ).first()

        if not ticker:
            return {}

        return {
            'lastPrice': ticker.lastPrice,
            'priceChangePercent': ticker.priceChangePercent,
            'openPrice': ticker.openPrice,
            'highPrice': ticker.highPrice,
            'lowPrice': ticker.lowPrice,
            'volume': ticker.volume,
            'quoteVolume': ticker.quoteVolume,
            'timestamp': ticker.timestamp.isoformat()
        }



    def get_candlestick_data(self, days: int = 90) -> list:
        cutoff = datetime.now() - timedelta(days=days)
        candles = self.db.query(CandlestickData).filter(
            CandlestickData.open_time >= cutoff
        ).order_by(CandlestickData.open_time).all()

        return candles



    def get_intraday_candles(self, limit: int = 6) -> list:
        candles = self.db.query(CandlestickIntradayModel).order_by(
            CandlestickIntradayModel.open_time.desc()
        ).limit(limit).all()

        if not candles:
            return []

        # Reverse to get chronological order (oldest to newest)
        candles = sorted(candles, key=lambda x: x.open_time)

        # Convert to clean dict list
        candle_data = []
        for candle in candles:
            candle_data.append({
                'open_time': candle.open_time.isoformat(),
                'close_time': candle.close_time.isoformat(),
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.volume,
                'quote_volume': candle.quote_volume,
                'num_trades': candle.num_trades,
                'taker_buy_base': candle.taker_buy_base,
                'taker_buy_quote': candle.taker_buy_quote
            })

        return candle_data



    def get_indicators_data(self, days: int = 30) -> dict:
        cutoff = datetime.now() - timedelta(days=days)
        indicators = self.db.query(IndicatorsData).filter(
            IndicatorsData.timestamp >= cutoff
        ).order_by(IndicatorsData.timestamp.desc()).first()

        if not indicators:
            return {}

        return {
            "timestamp": indicators.timestamp,
            "ema20": indicators.ema20,
            "ema50": indicators.ema50,
            "ema200": indicators.ema200,
            "rsi14": indicators.rsi14,
            "macd_line": indicators.macd_line,
            "macd_signal": indicators.macd_signal,
            "macd_histogram": indicators.macd_histogram,
            "bb_upper": indicators.bb_upper,
            "bb_middle": indicators.bb_middle,
            "bb_lower": indicators.bb_lower,
            "support1": indicators.support1,
            "support1_percent": indicators.support1_percent,
            "support2": indicators.support2,
            "support2_percent": indicators.support2_percent,
            "support3": indicators.support3,
            "support3_percent": indicators.support3_percent,
            "resistance1": indicators.resistance1,
            "resistance1_percent": indicators.resistance1_percent,
            "resistance2": indicators.resistance2,
            "resistance2_percent": indicators.resistance2_percent,
            "resistance3": indicators.resistance3,
            "resistance3_percent": indicators.resistance3_percent,
            "fib_level_0": indicators.fib_level_0,
            "fib_level_236": indicators.fib_level_236,
            "fib_level_382": indicators.fib_level_382,
            "fib_level_500": indicators.fib_level_500,
            "fib_level_618": indicators.fib_level_618,
            "fib_level_786": indicators.fib_level_786,
            "fib_level_100": indicators.fib_level_100,
            "pivot": indicators.pivot,
            "pivot_s1": indicators.pivot_s1,
            "pivot_s2": indicators.pivot_s2,
            "pivot_r1": indicators.pivot_r1,
            "pivot_r2": indicators.pivot_r2,
        }



    def get_trade_history(self, limit: int = 5) -> list:
        decisions = self.db.query(TradeDecision).order_by(
            TradeDecision.timestamp.desc()
        ).limit(limit).all()

        return [{
            "timestamp": d.timestamp,
            "decision": d.decision,
            "confidence": d.confidence,
            "reasoning": d.reasoning,
        } for d in decisions]
