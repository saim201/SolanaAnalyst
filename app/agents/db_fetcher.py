import sys
import os
from datetime import datetime, timedelta

from app.database.config import get_db_session
from app.database.models.candlestick import CandlestickModel, CandlestickIntradayModel, TickerModel
from app.database.models.news import NewsModel
from app.database.models.indicators import IndicatorsModel
from app.database.models.analysis import TraderAnalyst



class DataQuery:
    def __init__(self):
        self.db = get_db_session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def get_news_data(self, days: int = 7) -> list:
        cutoff = datetime.now() - timedelta(days=days)
        news = self.db.query(NewsModel).filter(
            NewsModel.published_at >= cutoff
        ).order_by(NewsModel.priority, NewsModel.published_at.desc()).all()

        if not news:
            return []

        news_data = []
        for article in news:
            news_data.append({
                'title': article.title,
                'url': article.url,
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
        candles = self.db.query(CandlestickModel).filter(
            CandlestickModel.open_time >= cutoff
        ).order_by(CandlestickModel.open_time).all()

        if not candles:
            return []

        # Reverse to get chronological order (oldest to newest)
        candles = sorted(candles, key=lambda x: x.open_time)

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



    def get_intraday_candles(self, limit: int = 6) -> list:
        candles = self.db.query(CandlestickIntradayModel).order_by(
            CandlestickIntradayModel.open_time.desc()
        ).limit(limit).all()

        if not candles:
            return []

        # Reverse to get chronological order (oldest to newest)
        candles = sorted(candles, key=lambda x: x.open_time)

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
        indicators = self.db.query(IndicatorsModel).filter(
            IndicatorsModel.timestamp >= cutoff
        ).order_by(IndicatorsModel.timestamp.desc()).first()

        if not indicators:
            return {}

        return {
            "timestamp": indicators.timestamp,

            # Trend
            "ema20": indicators.ema20,
            "ema50": indicators.ema50,
            "high_14d": indicators.high_14d,
            "low_14d": indicators.low_14d,

            # Momentum
            "macd_line": indicators.macd_line,
            "macd_signal": indicators.macd_signal,
            "macd_histogram": indicators.macd_histogram,
            "rsi14": indicators.rsi14,
            "rsi_divergence_type": indicators.rsi_divergence_type,
            "rsi_divergence_strength": indicators.rsi_divergence_strength,

            # Volatility
            "bb_upper": indicators.bb_upper,
            "bb_lower": indicators.bb_lower,
            "bb_squeeze_ratio": indicators.bb_squeeze_ratio,
            "bb_squeeze_active": indicators.bb_squeeze_active == 'True',
            "atr": indicators.atr,
            "atr_percent": indicators.atr_percent,

            # Volume
            "volume_ma20": indicators.volume_ma20,
            "volume_current": indicators.volume_current,
            "volume_ratio": indicators.volume_ratio,
            "volume_classification": indicators.volume_classification,
            "weighted_buy_pressure": indicators.weighted_buy_pressure,
            "days_since_volume_spike": indicators.days_since_volume_spike,

            # Support/Resistance Levels
            "support1": indicators.support1,
            "support1_percent": indicators.support1_percent,
            "support2": indicators.support2,
            "support2_percent": indicators.support2_percent,
            "resistance1": indicators.resistance1,
            "resistance1_percent": indicators.resistance1_percent,
            "resistance2": indicators.resistance2,
            "resistance2_percent": indicators.resistance2_percent,

            # BTC Correlation
            "btc_price_change_30d": indicators.btc_price_change_30d,
            "btc_trend": indicators.btc_trend,
            "sol_btc_correlation": indicators.sol_btc_correlation,
        }



    def get_trade_history(self, limit: int = 5) -> list:
        decisions = self.db.query(TraderAnalyst).order_by(
            TraderAnalyst.timestamp.desc()
        ).limit(limit).all()

        return [{
            "timestamp": d.timestamp,
            "decision": d.decision,
            "confidence": d.confidence,
            "reasoning": d.reasoning,
        } for d in decisions]




if __name__ == "__main__":
    import pprint
    dq = DataQuery()
    pprint.pp(dq.get_news_data())