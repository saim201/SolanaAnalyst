"""
Format market data and indicators into structured LLM payload
"""
from datetime import datetime, timedelta
from typing import Dict, List
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.config import get_db_session
from database.models import CandlestickData, CandlestickIntradayModel, TickerModel, IndicatorsData, TradeDecision


class LLMDataFormatter:
    """Format technical analysis data for LLM consumption"""

    @staticmethod
    def get_current_snapshot() -> Dict:
        """Get latest 24h ticker snapshot"""
        db = get_db_session()
        try:
            ticker = db.query(TickerModel).order_by(TickerModel.timestamp.desc()).first()

            if not ticker:
                return {}

            return {
                'timestamp': ticker.timestamp.isoformat(),
                'price': float(ticker.lastPrice),
                'price_change_24h_percent': float(ticker.priceChangePercent),
                'high_24h': float(ticker.highPrice),
                'low_24h': float(ticker.lowPrice),
                'volume_24h': float(ticker.volume),
            }
        finally:
            db.close()

    @staticmethod
    def get_intraday_candles_4h() -> List[Dict]:
        """Get last 24h of 4h intraday candles for entry timing"""
        db = get_db_session()
        try:
            cutoff = datetime.now() - timedelta(hours=24)
            candles = db.query(CandlestickIntradayModel).filter(
                CandlestickIntradayModel.open_time >= cutoff
            ).order_by(CandlestickIntradayModel.open_time).all()

            result = []
            for candle in candles:
                result.append({
                    'time': candle.open_time.isoformat(),
                    'open': float(candle.open),
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close),
                    'volume': float(candle.volume),
                })

            return result
        finally:
            db.close()

    @staticmethod
    def get_daily_candles_sliced() -> Dict:
        """
        Get last 90 days of daily candles sliced for swing trading:
        - Last 7 days (FULL DETAIL - trading window)
        - Days 8-30 (WEEKLY summary - trend context)
        - Days 31-90 (MONTHLY summary - longer trend)
        """
        db = get_db_session()
        try:
            now = datetime.now()
            cutoff_7d = now - timedelta(days=7)
            cutoff_30d = now - timedelta(days=30)
            cutoff_90d = now - timedelta(days=90)

            # Last 7 days - FULL DETAIL
            candles_7d = db.query(CandlestickData).filter(
                CandlestickData.open_time >= cutoff_7d
            ).order_by(CandlestickData.open_time).all()

            # Days 8-30 - WEEKLY (every ~5-7 days)
            candles_30d = db.query(CandlestickData).filter(
                CandlestickData.open_time >= cutoff_30d,
                CandlestickData.open_time < cutoff_7d
            ).order_by(CandlestickData.open_time).all()

            # Days 31-90 - MONTHLY (every ~30 days)
            candles_90d = db.query(CandlestickData).filter(
                CandlestickData.open_time >= cutoff_90d,
                CandlestickData.open_time < cutoff_30d
            ).order_by(CandlestickData.open_time).all()

            def format_candle(c):
                return {
                    'time': c.open_time.isoformat(),
                    'open': float(c.open),
                    'high': float(c.high),
                    'low': float(c.low),
                    'close': float(c.close),
                    'volume': float(c.volume),
                }

            return {
                'last_7d_detail': [format_candle(c) for c in candles_7d],
                'days_8_30_weekly': [format_candle(c) for c in candles_30d[::max(1, len(candles_30d)//4)]],
                'days_31_90_monthly': [format_candle(c) for c in candles_90d[::max(1, len(candles_90d)//2)]],
            }
        finally:
            db.close()

    @staticmethod
    def get_indicators_data() -> Dict:
        """Get latest calculated indicators: daily (PRIMARY) + 4h (SECONDARY)"""
        db = get_db_session()
        try:
            indicators = db.query(IndicatorsData).order_by(
                IndicatorsData.timestamp.desc()
            ).first()

            if not indicators:
                return {}

            return {
                'timestamp': indicators.timestamp.isoformat(),
                'daily': {
                    'trend': {
                        'ema20': float(indicators.ema20) if indicators.ema20 else None,
                        'ema50': float(indicators.ema50) if indicators.ema50 else None,
                        'ema200': float(indicators.ema200) if indicators.ema200 else None,
                    },
                    'momentum': {
                        'rsi14': float(indicators.rsi14) if indicators.rsi14 else None,
                        'macd_line': float(indicators.macd_line) if indicators.macd_line else None,
                        'macd_signal': float(indicators.macd_signal) if indicators.macd_signal else None,
                        'macd_histogram': float(indicators.macd_histogram) if indicators.macd_histogram else None,
                    },
                    'volatility': {
                        'bb_upper': float(indicators.bb_upper) if indicators.bb_upper else None,
                        'bb_middle': float(indicators.bb_middle) if indicators.bb_middle else None,
                        'bb_lower': float(indicators.bb_lower) if indicators.bb_lower else None,
                        'bb_width': float(indicators.bb_width) if indicators.bb_width else None,
                        'bb_position': float(indicators.bb_position) if indicators.bb_position else None,
                        'atr': float(indicators.atr) if indicators.atr else None,
                        'volatility_percent': float(indicators.volatility_percent) if indicators.volatility_percent else None,
                    },
                    'volume': {
                        'volume_ma20': float(indicators.volume_ma20) if indicators.volume_ma20 else None,
                        'volume_current': float(indicators.volume_current) if indicators.volume_current else None,
                        'volume_ratio': float(indicators.volume_ratio) if indicators.volume_ratio else None,
                        'obv': float(indicators.obv) if indicators.obv else None,
                        'buy_pressure_ratio': float(indicators.buy_pressure_ratio) if indicators.buy_pressure_ratio else None,
                    },
                    'support_resistance': {
                        'support': [
                            {'level': float(indicators.support1) if indicators.support1 else None, 'distance_percent': float(indicators.support1_percent) if indicators.support1_percent else None},
                            {'level': float(indicators.support2) if indicators.support2 else None, 'distance_percent': float(indicators.support2_percent) if indicators.support2_percent else None},
                            {'level': float(indicators.support3) if indicators.support3 else None, 'distance_percent': float(indicators.support3_percent) if indicators.support3_percent else None},
                        ],
                        'resistance': [
                            {'level': float(indicators.resistance1) if indicators.resistance1 else None, 'distance_percent': float(indicators.resistance1_percent) if indicators.resistance1_percent else None},
                            {'level': float(indicators.resistance2) if indicators.resistance2 else None, 'distance_percent': float(indicators.resistance2_percent) if indicators.resistance2_percent else None},
                            {'level': float(indicators.resistance3) if indicators.resistance3 else None, 'distance_percent': float(indicators.resistance3_percent) if indicators.resistance3_percent else None},
                        ],
                    },
                    'fibonacci': {
                        'fib_0': float(indicators.fib_level_0) if indicators.fib_level_0 else None,
                        'fib_236': float(indicators.fib_level_236) if indicators.fib_level_236 else None,
                        'fib_382': float(indicators.fib_level_382) if indicators.fib_level_382 else None,
                        'fib_500': float(indicators.fib_level_500) if indicators.fib_level_500 else None,
                        'fib_618': float(indicators.fib_level_618) if indicators.fib_level_618 else None,
                        'fib_786': float(indicators.fib_level_786) if indicators.fib_level_786 else None,
                        'fib_100': float(indicators.fib_level_100) if indicators.fib_level_100 else None,
                    },
                    'pivot_points': {
                        'pivot': float(indicators.pivot) if indicators.pivot else None,
                        'support1': float(indicators.pivot_s1) if indicators.pivot_s1 else None,
                        'support2': float(indicators.pivot_s2) if indicators.pivot_s2 else None,
                        'resistance1': float(indicators.pivot_r1) if indicators.pivot_r1 else None,
                        'resistance2': float(indicators.pivot_r2) if indicators.pivot_r2 else None,
                    },
                },
                'intraday_4h': {
                    'momentum': {
                        'ema20_4h': float(indicators.ema20_4h) if indicators.ema20_4h else None,
                        'ema50_4h': float(indicators.ema50_4h) if indicators.ema50_4h else None,
                        'rsi14_4h': float(indicators.rsi14_4h) if indicators.rsi14_4h else None,
                    },
                    'volatility': {
                        'high_4h': float(indicators.high_4h) if indicators.high_4h else None,
                        'low_4h': float(indicators.low_4h) if indicators.low_4h else None,
                        'range_4h': float(indicators.range_4h) if indicators.range_4h else None,
                        'price_from_low_4h': float(indicators.price_from_low_4h) if indicators.price_from_low_4h else None,
                    },
                },
            }
        finally:
            db.close()

    @staticmethod
    def get_recent_decisions(limit: int = 5) -> List[Dict]:
        """Get recent trade decisions for reflection"""
        db = get_db_session()
        try:
            decisions = db.query(TradeDecision).order_by(
                TradeDecision.timestamp.desc()
            ).limit(limit).all()

            return [{
                'timestamp': d.timestamp.isoformat(),
                'decision': d.decision,
                'confidence': float(d.confidence),
                'action': float(d.action),
                'reasoning': d.reasoning,
            } for d in reversed(decisions)]
        finally:
            db.close()

    @staticmethod
    def format_for_technical_agent() -> Dict:
        """
        Format data for technical analysis (PRIMARY - swing trading thesis)
        Input: Multi-timeframe indicators + price structure
        Focus: Price action, trends, momentum, support/resistance
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'current_snapshot': LLMDataFormatter.get_current_snapshot(),
            'intraday_4h': LLMDataFormatter.get_intraday_candles_4h(),
            'daily_candles': LLMDataFormatter.get_daily_candles_sliced(),
            'indicators': LLMDataFormatter.get_indicators_data(),
        }

    @staticmethod
    def format_for_news_agent() -> Dict:
        """
        Format data for news analysis (SECONDARY - market sentiment)
        Input: Recent news articles with sentiment
        Focus: Catalysts, sentiment direction, event impact
        """
        from database.models import NewsData
        db = get_db_session()
        try:
            cutoff = datetime.now() - timedelta(days=7)
            news_articles = db.query(NewsData).filter(
                NewsData.published_at >= cutoff
            ).order_by(NewsData.published_at.desc()).all()

            formatted_articles = []
            for article in news_articles:
                formatted_articles.append({
                    'title': article.title,
                    'source': article.source,
                    'published_at': article.published_at.isoformat(),
                    'sentiment': article.sentiment or 'neutral',
                    'url': article.url,
                })

            return {
                'timestamp': datetime.now().isoformat(),
                'articles_count': len(formatted_articles),
                'articles': formatted_articles,
                'period_days': 7,
            }
        finally:
            db.close()

    @staticmethod
    def format_for_reflection_agent() -> Dict:
        """
        Format data for reflection analysis (TERTIARY - strategy review)
        Input: Recent trade decisions and outcomes
        Focus: Decision quality, confidence calibration, pattern recognition
        """
        db = get_db_session()
        try:
            trades = db.query(TradeDecision).order_by(
                TradeDecision.timestamp.desc()
            ).limit(5).all()

            formatted_trades = []
            for trade in reversed(trades):
                formatted_trades.append({
                    'timestamp': trade.timestamp.isoformat(),
                    'decision': trade.decision,
                    'confidence': float(trade.confidence),
                    'action': float(trade.action),
                    'reasoning': trade.reasoning,
                })

            return {
                'timestamp': datetime.now().isoformat(),
                'trades_count': len(formatted_trades),
                'trades': formatted_trades,
                'period': 'recent 5 trades',
            }
        finally:
            db.close()

    @staticmethod
    def format_for_llm() -> Dict:
        """Legacy method - redirects to technical agent format"""
        return LLMDataFormatter.format_for_technical_agent()
