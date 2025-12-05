"""
Format market data and indicators into optimized LLM payload.

Single responsibility: Transform raw DB data into structured JSON
suitable for Claude AI analysis.

Uses db_fetcher for data access, builds optimal context structure.
"""
from datetime import datetime
from typing import Dict, List
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_fetcher import DataQuery


class LLMDataFormatter:

    @staticmethod
    def build_technical_context() -> Dict:
        dq = DataQuery()

        return {
            "timestamp": datetime.now().isoformat(),
            "current_snapshot": dq.get_ticker_data(),
            "today_4h_candles": dq.get_intraday_candles(limit=6),
            "last_7d_daily": dq.get_candlestick_data(days=7),
            "medium_30d": LLMDataFormatter._aggregate_weekly(
                dq.get_candlestick_data(days=30)[7:] if len(dq.get_candlestick_data(days=30)) > 7 else []
            ),
            "long_90d": LLMDataFormatter._aggregate_monthly(
                dq.get_candlestick_data(days=90)[30:] if len(dq.get_candlestick_data(days=90)) > 30 else []
            ),
            "indicators": LLMDataFormatter._format_indicators(dq.get_indicators_data()),
        }

    @staticmethod
    def _aggregate_weekly(candles: List[Dict]) -> List[Dict]:
        if not candles:
            return []

        # Return every 7th candle or fewer if not enough data
        step = max(1, len(candles) // 4)
        return candles[::step]


    @staticmethod
    def _aggregate_monthly(candles: List[Dict]) -> List[Dict]:
        if not candles:
            return []

        # Return every ~30th candle or fewer if not enough data
        step = max(1, len(candles) // 2)
        return candles[::step]

    @staticmethod
    def _format_indicators(indicators: Dict) -> Dict:
        if not indicators:
            return {}

        return {
            'timestamp': indicators.get('timestamp'),
            'daily': {
                'trend': {
                    'ema20': indicators.get('ema20'),
                    'ema50': indicators.get('ema50'),
                    'ema200': indicators.get('ema200'),
                },
                'momentum': {
                    'rsi14': indicators.get('rsi14'),
                    'macd_line': indicators.get('macd_line'),
                    'macd_signal': indicators.get('macd_signal'),
                    'macd_histogram': indicators.get('macd_histogram'),
                },
                'volatility': {
                    'bb_upper': indicators.get('bb_upper'),
                    'bb_middle': indicators.get('bb_middle'),
                    'bb_lower': indicators.get('bb_lower'),
                    'bb_width': indicators.get('bb_width'),
                    'bb_position': indicators.get('bb_position'),
                    'atr': indicators.get('atr'),
                    'volatility_percent': indicators.get('volatility_percent'),
                },
                'volume': {
                    'volume_ma20': indicators.get('volume_ma20'),
                    'volume_current': indicators.get('volume_current'),
                    'volume_ratio': indicators.get('volume_ratio'),
                    'obv': indicators.get('obv'),
                    'buy_pressure_ratio': indicators.get('buy_pressure_ratio'),
                },
                'support_resistance': {
                    'support': [
                        {
                            'level': indicators.get('support1'),
                            'distance_percent': indicators.get('support1_percent')
                        },
                        {
                            'level': indicators.get('support2'),
                            'distance_percent': indicators.get('support2_percent')
                        },
                        {
                            'level': indicators.get('support3'),
                            'distance_percent': indicators.get('support3_percent')
                        },
                    ],
                    'resistance': [
                        {
                            'level': indicators.get('resistance1'),
                            'distance_percent': indicators.get('resistance1_percent')
                        },
                        {
                            'level': indicators.get('resistance2'),
                            'distance_percent': indicators.get('resistance2_percent')
                        },
                        {
                            'level': indicators.get('resistance3'),
                            'distance_percent': indicators.get('resistance3_percent')
                        },
                    ],
                },
                'fibonacci': {
                    'fib_0': indicators.get('fib_level_0'),
                    'fib_236': indicators.get('fib_level_236'),
                    'fib_382': indicators.get('fib_level_382'),
                    'fib_500': indicators.get('fib_level_500'),
                    'fib_618': indicators.get('fib_level_618'),
                    'fib_786': indicators.get('fib_level_786'),
                    'fib_100': indicators.get('fib_level_100'),
                },
                'pivot_points': {
                    'pivot': indicators.get('pivot'),
                    'support1': indicators.get('pivot_s1'),
                    'support2': indicators.get('pivot_s2'),
                    'resistance1': indicators.get('pivot_r1'),
                    'resistance2': indicators.get('pivot_r2'),
                },
            },
            'intraday_4h': {
                'trend': {
                    'ema20_4h': indicators.get('ema20_4h'),
                    'ema50_4h': indicators.get('ema50_4h'),
                },
                'volatility': {
                    'high_4h': indicators.get('high_4h'),
                    'low_4h': indicators.get('low_4h'),
                    'range_4h': indicators.get('range_4h'),
                    'price_from_low_4h': indicators.get('price_from_low_4h'),
                },
            },
        }

    @staticmethod
    def get_recent_decisions(limit: int = 5) -> List[Dict]:
        """Get recent trade decisions for reflection"""
        dq = DataQuery()
        decisions = dq.get_trade_history(limit=limit)
        return decisions if decisions else []

    # ============ BACKWARD COMPATIBILITY LAYER ============
    # These methods delegate to build_technical_context() but maintain old interface

    @staticmethod
    def format_for_technical_agent() -> Dict:
        return LLMDataFormatter.build_technical_context()

    @staticmethod
    def format_for_news_agent() -> Dict:
        dq = DataQuery()
        news_articles = dq.get_news_data(days=7)

        return {
            'timestamp': datetime.now().isoformat(),
            'articles_count': len(news_articles),
            'articles': news_articles,
            'period_days': 7,
        }

    @staticmethod
    def format_for_reflection_agent() -> Dict:
        dq = DataQuery()
        trades = dq.get_trade_history(limit=5)

        return {
            'timestamp': datetime.now().isoformat(),
            'trades_count': len(trades),
            'trades': trades,
            'period': 'recent 5 trades',
        }

