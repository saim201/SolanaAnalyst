
from datetime import datetime
from typing import Dict, List
import sys
import os

from app.agents.db_fetcher import DataQuery


class LLMDataFormatter:

    @staticmethod
    def _interpret_trend(ema20: float, ema50: float, current_price: float) -> str:
        """Interpret trend structure from EMAs"""
        if current_price > ema20 > ema50:
            strength = ((current_price - ema50) / ema50) * 100
            return f"Strong bullish structure (price {strength:.1f}% above EMA50)"
        elif current_price > ema20 and ema20 < ema50:
            return "Weak bullish structure (consolidation - EMA20 below EMA50)"
        elif current_price < ema20 and ema20 > ema50:
            return "Weak bearish structure (potential reversal)"
        elif current_price < ema20 < ema50:
            strength = ((ema50 - current_price) / ema50) * 100
            return f"Strong bearish structure (price {strength:.1f}% below EMA50)"
        else:
            return "Range-bound structure (mixed signals)"

    @staticmethod
    def _interpret_momentum(rsi: float, macd_hist: float, divergence_type: str) -> str:
        """Interpret momentum from RSI, MACD, and divergence"""
        if divergence_type == "BEARISH":
            return f"⚠️ BEARISH DIVERGENCE - reversal risk despite RSI={rsi:.0f}"
        elif divergence_type == "BULLISH":
            return f"✅ BULLISH DIVERGENCE - reversal signal from oversold RSI={rsi:.0f}"

        if rsi < 30 and macd_hist > 0:
            return f"Oversold bounce signal (RSI={rsi:.0f}, MACD bullish)"
        elif rsi > 70 and macd_hist < 0:
            return f"Overbought correction signal (RSI={rsi:.0f}, MACD bearish)"
        elif macd_hist > 2 and rsi > 50:
            return f"Strong bullish momentum (RSI={rsi:.0f}, MACD expanding)"
        elif macd_hist < -2 and rsi < 50:
            return f"Strong bearish momentum (RSI={rsi:.0f}, MACD expanding down)"
        else:
            return f"Neutral momentum (RSI={rsi:.0f}, MACD histogram={macd_hist:+.2f})"

    @staticmethod
    def _interpret_risk_reward(support_dist: float, resistance_dist: float) -> str:
        """Interpret risk/reward ratio from nearest levels"""
        if support_dist is None or resistance_dist is None:
            return "Unable to calculate - missing support or resistance"

        risk = abs(support_dist)
        reward = resistance_dist

        if risk == 0:
            return "Invalid - no support identified"

        rr_ratio = reward / risk

        if rr_ratio >= 2.5:
            return f"Excellent R:R {rr_ratio:.1f}:1 ✅"
        elif rr_ratio >= 1.8:
            return f"Good R:R {rr_ratio:.1f}:1"
        elif rr_ratio >= 1.5:
            return f"Acceptable R:R {rr_ratio:.1f}:1 (minimum threshold)"
        else:
            return f"Poor R:R {rr_ratio:.1f}:1 ❌ (insufficient reward)"

    @staticmethod
    def build_technical_context() -> Dict:
        dq = DataQuery()

        intraday_candles = dq.get_intraday_candles(limit=6)
        candles_7d = dq.get_candlestick_data(days=7)
        candles_30d = dq.get_candlestick_data(days=30)
        candles_90d = dq.get_candlestick_data(days=90)

        return {
            "timestamp": datetime.now().isoformat(),
            "current_snapshot": dq.get_ticker_data(),
            "intraday_4h_pattern": LLMDataFormatter._summarize_4h_pattern(intraday_candles),
            "price_trends": {
                "last_7d": LLMDataFormatter._summarize_7d(candles_7d),
                "trend_30d": LLMDataFormatter._summarize_30d_trend(candles_30d),
                "trend_90d": LLMDataFormatter._summarize_90d_trend(candles_90d),
            },
            "indicators": LLMDataFormatter._format_indicators(dq.get_indicators_data()),
        }



    @staticmethod
    def _aggregate_weekly(candles: List[Dict]) -> List[Dict]:
        if not candles:
            return []
        step = max(1, len(candles) // 4)
        return candles[::step]


    @staticmethod
    def _aggregate_monthly(candles: List[Dict]) -> List[Dict]:
        if not candles:
            return []
        step = max(1, len(candles) // 2)
        return candles[::step]



    @staticmethod
    def _summarize_4h_pattern(candles: List[Dict]) -> str:
        if not candles or len(candles) == 0:
            return "insufficient data"

        opens = [float(c['open']) for c in candles]
        closes = [float(c['close']) for c in candles]
        highs = [float(c['high']) for c in candles]
        lows = [float(c['low']) for c in candles]

        first_open = opens[0]
        last_close = closes[-1]
        pattern_change = ((last_close - first_open) / first_open) * 100

        high = max(highs)
        low = min(lows)
        range_size = high - low

        up_candles = sum(1 for i in range(len(closes)) if closes[i] > opens[i])
        momentum = "accelerating" if up_candles >= 4 else "decelerating" if up_candles <= 2 else "mixed"

        if pattern_change > 1:
            trend = "rising"
        elif pattern_change < -1:
            trend = "falling"
        else:
            trend = "neutral"

        return f"{trend} {pattern_change:+.1f}%, {momentum}, range ${low:.2f}-${high:.2f}"



    @staticmethod
    def _summarize_7d(candles: List[Dict]) -> str:
        if not candles or len(candles) == 0:
            return "no data"

        first_open = float(candles[0]['open'])
        last_close = float(candles[-1]['close'])
        change_pct = ((last_close - first_open) / first_open) * 100

        highs = [float(c['high']) for c in candles]
        lows = [float(c['low']) for c in candles]

        high = max(highs)
        low = min(lows)

        return f"{change_pct:+.1f}% (${low:.2f}-${high:.2f})"



    @staticmethod
    def _summarize_30d_trend(candles: List[Dict]) -> str:
        if not candles or len(candles) < 10:
            return "insufficient data"

        first_open = float(candles[0]['open'])
        last_close = float(candles[-1]['close'])
        change_pct = ((last_close - first_open) / first_open) * 100

        closes = [float(c['close']) for c in candles]
        ema20 = sum(closes[-20:]) / min(20, len(closes[-20:]))

        current = closes[-1]
        above_ema = current > ema20

        if change_pct > 10 and above_ema:
            return "strong bull"
        elif change_pct > 2 and above_ema:
            return "uptrend"
        elif change_pct < -10 and not above_ema:
            return "strong bear"
        elif change_pct < -2 and not above_ema:
            return "downtrend"
        else:
            return "range-bound"



    @staticmethod
    def _summarize_90d_trend(candles: List[Dict]) -> str:
        if not candles or len(candles) < 60:
            return "insufficient data"
        
        closes = [float(c['close']) for c in candles]
        
        if len(closes) < 60:
            return "insufficient data"
        
        # EMAs for trend structure
        ema20 = sum(closes[-20:]) / min(20, len(closes[-20:]))
        ema50 = sum(closes[-50:]) / min(50, len(closes[-50:]))
        
        first_close = closes[0]
        last_close = closes[-1]
        change_pct = ((last_close - first_close) / first_close) * 100
        
        current = closes[-1]
        
        # Determine quarterly trend regime
        if current > ema50 and ema20 > ema50 and change_pct > 15:
            return "strong bull market"
        elif current > ema50 and change_pct > 5:
            return "bull market"
        elif current < ema50 and ema20 < ema50 and change_pct < -15:
            return "strong bear market"
        elif current < ema50 and change_pct < -5:
            return "bear market"
        elif abs(change_pct) < 5:
            return "range-bound consolidation"
        else:
            return "transitional (trend unclear)"



    @staticmethod
    def _format_indicators(indicators: Dict) -> Dict:
        if not indicators:
            return {}

        from app.data.indicators import classify_volume_quality

        return {
            'timestamp': indicators.get('timestamp'),
            'trend': {
                'ema20': indicators.get('ema20'),
                'ema50': indicators.get('ema50'),
                'ema200': indicators.get('ema200'),  # KEPT: Major trend bias
            },
            'momentum': {
                'rsi14': indicators.get('rsi14'),
                'rsi_divergence_type': indicators.get('rsi_divergence_type', 'NONE'),
                'rsi_divergence_strength': indicators.get('rsi_divergence_strength', 0.0),
                'macd_line': indicators.get('macd_line'),
                'macd_signal': indicators.get('macd_signal'),
                'macd_histogram': indicators.get('macd_histogram'),
            },
            'volatility': {
                'bb_upper': indicators.get('bb_upper'),
                'bb_lower': indicators.get('bb_lower'),
                'atr': indicators.get('atr'),
            },
            'volume': {
                'volume_ma20': indicators.get('volume_ma20'),
                'volume_current': indicators.get('volume_current'),
                'volume_ratio': indicators.get('volume_ratio'),
                'volume_quality': classify_volume_quality(indicators.get('volume_ratio', 1.0)),
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
                ],
            },
            'fibonacci': {
                'fib_382': indicators.get('fib_level_382'),
                'fib_618': indicators.get('fib_level_618'),
            },
            'pivot': {
                'weekly': indicators.get('pivot_weekly'),  # Market bias indicator
            },
            'ticker_24h': {
                'momentum_24h': indicators.get('momentum_24h'),
                'range_position_24h': indicators.get('range_position_24h'),
                'volume_surge_24h': indicators.get('volume_surge_24h'),
            },
        }



    @staticmethod
    def get_recent_decisions(limit: int = 5) -> List[Dict]:
        dq = DataQuery()
        decisions = dq.get_trade_history(limit=limit)
        return decisions if decisions else []


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

