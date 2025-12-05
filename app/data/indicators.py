
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, List


def classify_volume_quality(volume_ratio: float) -> dict:
    """
    Classify volume strength based on swing trading research.

    Research findings:
    - 7+ week consolidations need 1.4x volume (40%+ above average) for valid breakout
    - Low volume (<0.7x) indicates manipulation risk and false breakouts
    - Volume ratio is THE most important confirmation signal for swing trades
    """
    if volume_ratio >= 1.4:
        return {
            "classification": "STRONG",
            "description": "40%+ above average - high conviction move",
            "trading_allowed": True,
            "confidence_multiplier": 1.0
        }
    elif 1.0 <= volume_ratio < 1.4:
        return {
            "classification": "ACCEPTABLE",
            "description": "Average to slightly above - proceed with caution",
            "trading_allowed": True,
            "confidence_multiplier": 0.85
        }
    elif 0.7 <= volume_ratio < 1.0:
        return {
            "classification": "WEAK",
            "description": "Below average - high risk of false signal",
            "trading_allowed": True,
            "confidence_multiplier": 0.6
        }
    else:  # < 0.7
        return {
            "classification": "DEAD",
            "description": "Critically low - manipulation risk, false breakout likely",
            "trading_allowed": False,
            "confidence_multiplier": 0.0
        }


def detect_rsi_divergence(df: pd.DataFrame, rsi_series: pd.Series, lookback: int = 14) -> dict:
    """
    Detect bullish/bearish RSI divergence for reversal signals.

    Divergence types:
    - BULLISH: Price makes lower low, RSI makes higher low (reversal up)
    - BEARISH: Price makes higher high, RSI makes lower high (reversal down)
    - NONE: No divergence detected
    """
    if len(df) < lookback:
        return {"type": "NONE", "strength": 0.0}

    recent_df = df.tail(lookback).copy()
    recent_rsi = rsi_series.tail(lookback)

    try:
        # Check for bearish divergence (price higher high, RSI lower high)
        # Compare current vs 5 periods ago
        if len(recent_df) >= 6:
            price_current = recent_df['high'].iloc[-1]
            price_prev = recent_df['high'].iloc[-6]
            rsi_current = recent_rsi.iloc[-1]
            rsi_prev = recent_rsi.iloc[-6]

            # Bearish: Price up, RSI down
            if price_current > price_prev and rsi_current < rsi_prev:
                strength = min(abs(rsi_current - rsi_prev) / 20.0, 1.0)  # Normalize to 0-1
                return {"type": "BEARISH", "strength": float(strength)}

            # Bullish: Price down, RSI up
            price_low_current = recent_df['low'].iloc[-1]
            price_low_prev = recent_df['low'].iloc[-6]

            if price_low_current < price_low_prev and rsi_current > rsi_prev:
                strength = min(abs(rsi_current - rsi_prev) / 20.0, 1.0)
                return {"type": "BULLISH", "strength": float(strength)}

        return {"type": "NONE", "strength": 0.0}

    except Exception as e:
        print(f"⚠️  RSI divergence detection error: {e}")
        return {"type": "NONE", "strength": 0.0}




class IndicatorsCalculator:
    
    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        # Exponential Moving Average
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        # Relative Strength Index
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        #  MACD (Moving Average Convergence Divergence)
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)
        
        return upper, lower
    
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        # Average True Range
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def volume_ma(volume: pd.Series, period: int = 20) -> pd.Series:
        # Volume Moving Average
        return volume.rolling(window=period).mean()
    
    @staticmethod
    def volume_ratio(current_volume: float, volume_ma: float) -> float:
        # volume ratio to MA
        if volume_ma == 0:
            return 1.0
        return current_volume / volume_ma

    @staticmethod
    def pivot_points(prev_high: float, prev_low: float, prev_close: float) -> Dict[str, float]:
        pivot = (prev_high + prev_low + prev_close) / 3
        r1 = (2 * pivot) - prev_low
        r2 = pivot + (prev_high - prev_low)
        s1 = (2 * pivot) - prev_high
        s2 = pivot - (prev_high - prev_low)
        
        return {
            'pivot': pivot,
            'r1': r1,
            'r2': r2,
            's1': s1,
            's2': s2,
        }
    
    @staticmethod
    def fibonacci_retracement(swing_high: float, swing_low: float) -> Dict[str, float]:
        diff = swing_high - swing_low
        
        return {
            '0%': swing_high,
            '23.6%': swing_high - (diff * 0.236),
            '38.2%': swing_high - (diff * 0.382),
            '50%': swing_high - (diff * 0.5),
            '61.8%': swing_high - (diff * 0.618),
            '78.6%': swing_high - (diff * 0.786),
            '100%': swing_low,
        }
    
    @staticmethod
    def find_recent_swing(df: pd.DataFrame, lookback_days: int = 30) -> Tuple[float, float]:
        recent = df.tail(lookback_days)
        swing_high = recent['high'].max()
        swing_low = recent['low'].min()
        return swing_high, swing_low
    
    @staticmethod
    def find_support_resistance(df: pd.DataFrame, current_price: float, lookback_days: int = 30) -> Tuple[List[float], List[float]]:
        recent = df.tail(lookback_days)
        
        # Get EMA values
        ema20 = recent['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = recent['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = recent['close'].ewm(span=200, adjust=False).mean().iloc[-1]
        
        # Create candidate levels (EMAs + recent price zones)
        all_levels = [ema20, ema50, ema200]
        
        # Add high/low clusters (consolidation zones)
        highs = recent['high'].values
        lows = recent['low'].values
        
        # Find clusters of highs and lows
        for high in np.percentile(highs, [75, 90, 100]):
            all_levels.append(float(high))
        for low in np.percentile(lows, [0, 10, 25]):
            all_levels.append(float(low))
        
        # Separate into support (below) and resistance (above)
        support = sorted([level for level in all_levels if level < current_price], reverse=True)[:3]
        resistance = sorted([level for level in all_levels if level > current_price])[:3]
        
        # Pad with empty lists if needed
        while len(support) < 3:
            support.append(None)
        while len(resistance) < 3:
            resistance.append(None)
        
        return support[:3], resistance[:3]


class IndicatorsProcessor:    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> Dict:
        if df.empty or len(df) < 60:
            print(f"⚠️  Insufficient data for indicators (need 60 candles, got {len(df)})")
            return {}
        
        df = df.copy()
        df = df.sort_values('open_time').reset_index(drop=True)
        
        indicators = {}
        
        # Trend
        indicators['ema20'] = float(IndicatorsCalculator.ema(df['close'], 20).iloc[-1] or 0)
        indicators['ema50'] = float(IndicatorsCalculator.ema(df['close'], 50).iloc[-1] or 0)
        indicators['ema200'] = float(IndicatorsCalculator.ema(df['close'], 200).iloc[-1] or 0)
        
        macd_line, signal_line, histogram = IndicatorsCalculator.macd(df['close'])
        indicators['macd_line'] = float(macd_line.iloc[-1] or 0)
        indicators['macd_signal'] = float(signal_line.iloc[-1] or 0)
        indicators['macd_histogram'] = float(histogram.iloc[-1] or 0)
        
        # Calculate RSI series first
        rsi_series = IndicatorsCalculator.rsi(df['close'], 14)
        indicators['rsi14'] = float(rsi_series.iloc[-1] or 0)

        # Detect RSI divergence
        rsi_divergence = detect_rsi_divergence(df, rsi_series, lookback=14)
        indicators['rsi_divergence_type'] = rsi_divergence['type']
        indicators['rsi_divergence_strength'] = rsi_divergence['strength']

        bb_upper, bb_lower = IndicatorsCalculator.bollinger_bands(df['close'], 20, 2)
        indicators['bb_upper'] = float(bb_upper.iloc[-1] or 0)
        indicators['bb_lower'] = float(bb_lower.iloc[-1] or 0)

        current_price = float(df['close'].iloc[-1])
        
        atr = IndicatorsCalculator.atr(df, 14)
        indicators['atr'] = float(atr.iloc[-1] or 0)

        vol_ma = IndicatorsCalculator.volume_ma(df['volume'], 20)
        current_vol = float(df['volume'].iloc[-1])
        indicators['volume_ma20'] = float(vol_ma.iloc[-1] or 0)
        indicators['volume_current'] = current_vol
        indicators['volume_ratio'] = IndicatorsCalculator.volume_ratio(current_vol, indicators['volume_ma20'])
        
        
        # Fibonacci Retracement (ONLY 38.2% and 61.8% - key levels for swing trading)
        swing_high, swing_low = IndicatorsCalculator.find_recent_swing(df, 30)
        fib_levels = IndicatorsCalculator.fibonacci_retracement(swing_high, swing_low)
        indicators['fib_level_382'] = float(fib_levels['38.2%'])
        indicators['fib_level_618'] = float(fib_levels['61.8%'])
        # REMOVED: fib_level_236, fib_level_500

        # Weekly Pivot (for market bias, not intraday trading)
        # Calculate from last 7 days of data
        if len(df) >= 7:
            last_week = df.tail(7)
            week_high = float(last_week['high'].max())
            week_low = float(last_week['low'].min())
            week_close = float(last_week['close'].iloc[-1])

            # Weekly pivot formula: (H + L + C) / 3
            indicators['pivot_weekly'] = (week_high + week_low + week_close) / 3
        else:
            indicators['pivot_weekly'] = None

        
        # Support/Resistance 
        support_levels, resistance_levels = IndicatorsCalculator.find_support_resistance(df, current_price, 30)

        # Only process first 2 levels
        for i in range(1, 3):  # Changed from range(1, 4) to range(1, 3)
            if i-1 < len(support_levels) and support_levels[i-1]:
                level = support_levels[i-1]
                percent_diff = ((current_price - level) / current_price) * 100
                indicators[f'support{i}'] = float(level)
                indicators[f'support{i}_percent'] = float(percent_diff)
            else:
                indicators[f'support{i}'] = None
                indicators[f'support{i}_percent'] = None

        for i in range(1, 3):  # Changed from range(1, 4) to range(1, 3)
            if i-1 < len(resistance_levels) and resistance_levels[i-1]:
                level = resistance_levels[i-1]
                percent_diff = ((level - current_price) / current_price) * 100
                indicators[f'resistance{i}'] = float(level)
                indicators[f'resistance{i}_percent'] = float(percent_diff)
            else:
                indicators[f'resistance{i}'] = None
                indicators[f'resistance{i}_percent'] = None
        
        return indicators


    @staticmethod
    def calculate_ticker_indicators(ticker_data: Dict, volume_ma20: float) -> Dict:
        indicators = {}

        # Momentum 24h
        indicators['momentum_24h'] = float(ticker_data.get('priceChangePercent', 0))

        # Range Position 24h (0=at low, 1=at high)
        current = float(ticker_data['lastPrice'])
        high_24h = float(ticker_data['highPrice'])
        low_24h = float(ticker_data['lowPrice'])
        range_24h = high_24h - low_24h
        if range_24h > 0:
            indicators['range_position_24h'] = (current - low_24h) / range_24h
        else:
            indicators['range_position_24h'] = 0.5

        # Volume Surge 24h
        volume_24h = float(ticker_data['volume'])
        if volume_ma20 > 0:
            indicators['volume_surge_24h'] = volume_24h / volume_ma20
        else:
            indicators['volume_surge_24h'] = 1.0

        return indicators


if __name__ == "__main__":
    pass
