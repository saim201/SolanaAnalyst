
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, List


class IndicatorsCalculator:
    
    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)
        
        return upper, sma, lower
    
    @staticmethod
    def bb_position(close: float, upper: float, lower: float, middle: float) -> float:
        """Calculate Bollinger Bands position (0-1, where 0=lower, 0.5=middle, 1=upper)"""
        band_width = upper - lower
        if band_width == 0:
            return 0.5
        return (close - lower) / band_width
    
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
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
    def volatility_percent(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate volatility as percentage"""
        returns = df['close'].pct_change()
        volatility = returns.rolling(window=period).std() * 100
        return volatility
    
    @staticmethod
    def volume_ma(volume: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Volume Moving Average"""
        return volume.rolling(window=period).mean()
    
    @staticmethod
    def volume_ratio(current_volume: float, volume_ma: float) -> float:
        """Calculate volume ratio to MA"""
        if volume_ma == 0:
            return 1.0
        return current_volume / volume_ma
    

    @staticmethod
    def on_balance_volume(df: pd.DataFrame) -> pd.Series:
        obv_values = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv_values.append(obv_values[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv_values.append(obv_values[-1] - df['volume'].iloc[i])
            else:
                obv_values.append(obv_values[-1])
        return pd.Series(obv_values, index=df.index)

    @staticmethod
    def buy_pressure_ratio(taker_buy_volume: float, total_volume: float) -> float:
        if total_volume == 0:
            return 0.5
        return taker_buy_volume / total_volume

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
        
        # MACD
        macd_line, signal_line, histogram = IndicatorsCalculator.macd(df['close'])
        indicators['macd_line'] = float(macd_line.iloc[-1] or 0)
        indicators['macd_signal'] = float(signal_line.iloc[-1] or 0)
        indicators['macd_histogram'] = float(histogram.iloc[-1] or 0)
        
        # RSI
        indicators['rsi14'] = float(IndicatorsCalculator.rsi(df['close'], 14).iloc[-1] or 0)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = IndicatorsCalculator.bollinger_bands(df['close'], 20, 2)
        indicators['bb_upper'] = float(bb_upper.iloc[-1] or 0)
        indicators['bb_middle'] = float(bb_middle.iloc[-1] or 0)
        indicators['bb_lower'] = float(bb_lower.iloc[-1] or 0)
        indicators['bb_width'] = float((bb_upper.iloc[-1] - bb_lower.iloc[-1]) or 0)
        
        current_price = float(df['close'].iloc[-1])
        indicators['bb_position'] = IndicatorsCalculator.bb_position(
            current_price,
            indicators['bb_upper'],
            indicators['bb_lower'],
            indicators['bb_middle']
        )
        
        # ATR
        atr = IndicatorsCalculator.atr(df, 14)
        indicators['atr'] = float(atr.iloc[-1] or 0)
        
        # Volatility
        volatility = IndicatorsCalculator.volatility_percent(df, 20)
        indicators['volatility_percent'] = float(volatility.iloc[-1] or 0)
        
        # Volume
        vol_ma = IndicatorsCalculator.volume_ma(df['volume'], 20)
        current_vol = float(df['volume'].iloc[-1])
        indicators['volume_ma20'] = float(vol_ma.iloc[-1] or 0)
        indicators['volume_current'] = current_vol
        indicators['volume_ratio'] = IndicatorsCalculator.volume_ratio(current_vol, indicators['volume_ma20'])
        obv = IndicatorsCalculator.on_balance_volume(df)
        indicators['obv'] = float(obv.iloc[-1] or 0)
        
        latest_taker_buy = float(df['taker_buy_base'].iloc[-1]) if 'taker_buy_base' in df.columns else 0
        latest_vol = float(df['volume'].iloc[-1])
        buy_pressure = IndicatorsCalculator.buy_pressure_ratio(latest_taker_buy, latest_vol)
        indicators['buy_pressure_ratio'] = float(buy_pressure)
        
        
        # Fibonacci Retracement (from most recent swing in 30d)
        swing_high, swing_low = IndicatorsCalculator.find_recent_swing(df, 30)
        fib_levels = IndicatorsCalculator.fibonacci_retracement(swing_high, swing_low)
        indicators['fib_level_0'] = float(fib_levels['0%'])
        indicators['fib_level_236'] = float(fib_levels['23.6%'])
        indicators['fib_level_382'] = float(fib_levels['38.2%'])
        indicators['fib_level_500'] = float(fib_levels['50%'])
        indicators['fib_level_618'] = float(fib_levels['61.8%'])
        indicators['fib_level_786'] = float(fib_levels['78.6%'])
        indicators['fib_level_100'] = float(fib_levels['100%'])
        
        # Pivot Points (from previous day)
        if len(df) >= 2:
            prev_row = df.iloc[-2]
            pivot_data = IndicatorsCalculator.pivot_points(
                float(prev_row['high']),
                float(prev_row['low']),
                float(prev_row['close'])
            )
            indicators['pivot'] = pivot_data['pivot']
            indicators['pivot_s1'] = pivot_data['s1']
            indicators['pivot_s2'] = pivot_data['s2']
            indicators['pivot_r1'] = pivot_data['r1']
            indicators['pivot_r2'] = pivot_data['r2']
        
        # Support/Resistance (top 3 each)
        support_levels, resistance_levels = IndicatorsCalculator.find_support_resistance(df, current_price, 30)
        
        for i, level in enumerate(support_levels, 1):
            if level:
                percent_diff = ((current_price - level) / current_price) * 100
                indicators[f'support{i}'] = float(level)
                indicators[f'support{i}_percent'] = float(percent_diff)
            else:
                indicators[f'support{i}'] = None
                indicators[f'support{i}_percent'] = None
        
        for i, level in enumerate(resistance_levels, 1):
            if level:
                percent_diff = ((level - current_price) / current_price) * 100
                indicators[f'resistance{i}'] = float(level)
                indicators[f'resistance{i}_percent'] = float(percent_diff)
            else:
                indicators[f'resistance{i}'] = None
                indicators[f'resistance{i}_percent'] = None
        
        return indicators

    @staticmethod
    def calculate_intraday_indicators(df: pd.DataFrame) -> Dict:
        if df.empty or len(df) < 3:
            return {}

        df = df.copy()
        df = df.sort_values('open_time').reset_index(drop=True)

        indicators = {}

        indicators['ema20_4h'] = float(IndicatorsCalculator.ema(df['close'], 20).iloc[-1] or 0)
        indicators['ema50_4h'] = float(IndicatorsCalculator.ema(df['close'], 50).iloc[-1] or 0)

        current_price = float(df['close'].iloc[-1])
        high_4h = df['high'].max()
        low_4h = df['low'].min()
        indicators['high_4h'] = high_4h
        indicators['low_4h'] = low_4h
        indicators['range_4h'] = high_4h - low_4h
        indicators['price_from_low_4h'] = ((current_price - low_4h) / current_price) * 100 if current_price else 0

        return indicators


if __name__ == "__main__":
    pass
