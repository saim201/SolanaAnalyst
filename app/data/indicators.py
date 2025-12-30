
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, Tuple, List


def exclude_incomplete_candle_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove the most recent candle if it's from today (incomplete).

    THE BUG: When pipeline runs mid-day, the last daily candle only has
    partial volume (e.g., 6 hours instead of 24 hours). This makes
    volume_ratio appear extremely low (0.14x) when actual volume is normal.

    THE FIX: Exclude today's incomplete candle from volume calculations.
    """
    if df.empty or len(df) < 2:
        return df

    last_open_time = df['open_time'].iloc[-1]

    # Handle different date formats
    if isinstance(last_open_time, str):
        try:
            last_date = datetime.fromisoformat(last_open_time.replace('Z', '+00:00')).date()
        except:
            return df
    elif hasattr(last_open_time, 'date'):
        last_date = last_open_time.date()
    elif isinstance(last_open_time, date):
        last_date = last_open_time
    else:
        return df

    today = date.today()

    if last_date == today:
        print(f"✂️  Excluding incomplete candle from {last_date} for volume calculation")
        return df.iloc[:-1].copy()

    return df


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
    if len(df) < lookback or len(rsi_series) < lookback:
        return {"type": "NONE", "strength": 0.0}

    recent_df = df.tail(lookback).copy()
    recent_rsi = rsi_series.tail(lookback)

    try:
        # Check multiple lookback periods for divergence (3, 5, 7, 10, 14 candles)
        # Expanded range to catch divergences over longer timeframes
        for period in [3, 5, 7, 10, 14]:
            if len(recent_df) >= period + 1:
                price_current = recent_df['high'].iloc[-1]
                price_prev = recent_df['high'].iloc[-(period + 1)]
                price_low_current = recent_df['low'].iloc[-1]
                price_low_prev = recent_df['low'].iloc[-(period + 1)]

                rsi_current = recent_rsi.iloc[-1]
                rsi_prev = recent_rsi.iloc[-(period + 1)]

                # Bearish divergence: Price making higher high, RSI making lower high
                # Require at least 1% price increase for meaningful divergence
                price_change_pct = ((price_current - price_prev) / price_prev * 100) if price_prev > 0 else 0

                if price_change_pct > 1.0 and rsi_current < rsi_prev - 2:  # Price up >1%, RSI down >2 points
                    strength = min(abs(rsi_current - rsi_prev) / 20.0, 1.0)
                    return {"type": "BEARISH", "strength": float(strength)}

                # Bullish divergence: Price making lower low, RSI making higher low
                # Require at least 1% price decrease for meaningful divergence
                price_change_pct_low = ((price_low_current - price_low_prev) / price_low_prev * 100) if price_low_prev > 0 else 0

                if price_change_pct_low < -1.0 and rsi_current > rsi_prev + 2:  # Price down >1%, RSI up >2 points
                    strength = min(abs(rsi_current - rsi_prev) / 20.0, 1.0)
                    return {"type": "BULLISH", "strength": float(strength)}

        return {"type": "NONE", "strength": 0.0}

    except Exception as e:
        print(f"⚠️  RSI divergence detection error: {e}")
        import traceback
        traceback.print_exc()
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
    def calculate_vwap(df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate VWAP (Volume Weighted Average Price)
        VWAP = Σ(Price × Volume) / Σ(Volume)
        This is the institutional benchmark - price above VWAP = bullish control
        """
        if df.empty or len(df) < 1:
            return {'vwap': 0.0, 'vwap_distance_percent': 0.0}

        # Use typical price (high + low + close) / 3
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        total_pv = (typical_price * df['volume']).sum()
        total_volume = df['volume'].sum()
        vwap = total_pv / total_volume if total_volume > 0 else 0

        current_price = float(df['close'].iloc[-1])
        vwap_distance = ((current_price - vwap) / vwap) * 100 if vwap > 0 else 0

        return {
            'vwap': float(vwap),
            'vwap_distance_percent': float(vwap_distance)
        }

    @staticmethod
    def calculate_bb_squeeze(bb_upper: float, bb_lower: float, current_price: float) -> Dict[str, any]:
        """
        Calculate Bollinger Band Squeeze Ratio
        Squeeze Ratio = (BB Upper - BB Lower) / Price × 100
        Low ratio (<10%) = Tight squeeze = Breakout imminent
        """
        if current_price == 0:
            return {'bb_squeeze_ratio': 0.0, 'bb_squeeze_active': False}

        bb_width = bb_upper - bb_lower
        squeeze_ratio = (bb_width / current_price) * 100
        squeeze_active = squeeze_ratio < 10.0

        return {
            'bb_squeeze_ratio': float(squeeze_ratio),
            'bb_squeeze_active': bool(squeeze_active)
        }

    @staticmethod
    def calculate_weighted_buy_pressure(df: pd.DataFrame, periods: int = 7) -> float:
        """
        Calculate Weighted Buy Pressure with exponential decay
        Recent activity matters more - most recent candle = 40%, previous = 30%, etc.
        Returns: Buy pressure percentage (0-100)
        """
        if df.empty or len(df) < periods:
            return 50.0  # Neutral

        recent_candles = df.tail(periods)
        weights = [0.40, 0.30, 0.15, 0.10, 0.05]  # For last 5 candles

        if len(recent_candles) < 5:
            weights = weights[:len(recent_candles)]
            weight_sum = sum(weights)
            weights = [w / weight_sum for w in weights]

        weighted_pressure = 0.0
        for i, (_, candle) in enumerate(recent_candles.tail(min(5, len(recent_candles))).iterrows()):
            volume = candle.get('volume', 0)
            taker_buy = candle.get('taker_buy_base', 0)
            buy_ratio = (taker_buy / volume * 100) if volume > 0 else 50.0
            weighted_pressure += buy_ratio * weights[i]

        return float(weighted_pressure)

    @staticmethod
    def calculate_correlation(sol_prices: List[float], btc_prices: List[float]) -> float:
        """
        Calculate 30-day correlation coefficient between SOL and BTC
        Typical SOL-BTC correlation: 0.75-0.90
        """
        if len(sol_prices) < 2 or len(btc_prices) < 2:
            return 0.8  # Default assumption

        min_len = min(len(sol_prices), len(btc_prices))
        sol_prices = sol_prices[-min_len:]
        btc_prices = btc_prices[-min_len:]

        sol_series = pd.Series(sol_prices)
        btc_series = pd.Series(btc_prices)
        correlation = sol_series.corr(btc_series)

        if pd.isna(correlation):
            return 0.8  # Default

        return float(correlation)

    @staticmethod
    def kijun_sen(df: pd.DataFrame, period: int = 26) -> float:
        # Kijun-Sen (Base Line) - Ichimoku indicator for trend equilibrium
        recent = df.tail(period)
        return float((recent['high'].max() + recent['low'].min()) / 2)

    @staticmethod
    def stochastic_rsi(rsi_series: pd.Series, period: int = 14) -> float:
        # more sensitive overbought/oversold indicator
        recent_rsi = rsi_series.tail(period)
        rsi_min = recent_rsi.min()
        rsi_max = recent_rsi.max()

        if rsi_max == rsi_min:
            return 0.5

        stoch_rsi = (rsi_series.iloc[-1] - rsi_min) / (rsi_max - rsi_min)
        return float(stoch_rsi)

    @staticmethod
    def days_since_volume_spike(df: pd.DataFrame, spike_threshold: float = 1.5) -> int:
        #Days since last volume spike (>1.5x average)
        try:
            volume_ma20 = df['volume'].rolling(20).mean()
            spike_condition = df['volume'] > (volume_ma20 * spike_threshold)
            spike_indices = df[spike_condition].index

            if len(spike_indices) == 0:
                return 999  # No spike found

            last_spike_idx = spike_indices[-1]
            current_idx = df.index[-1]
            days_since = (current_idx - last_spike_idx)

            return int(days_since) if hasattr(days_since, 'days') else int(days_since)
        except:
            return 999

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

        ema20 = recent['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = recent['close'].ewm(span=50, adjust=False).mean().iloc[-1]

        all_levels = [ema20, ema50]
        
        highs = recent['high'].values
        lows = recent['low'].values
        
        for high in np.percentile(highs, [75, 90, 100]):
            all_levels.append(float(high))
        for low in np.percentile(lows, [0, 10, 25]):
            all_levels.append(float(low))
        
        support = sorted([level for level in all_levels if level < current_price], reverse=True)[:3]
        resistance = sorted([level for level in all_levels if level > current_price])[:3]
        
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

        # NEW: BB Squeeze calculation
        bb_squeeze = IndicatorsCalculator.calculate_bb_squeeze(
            indicators['bb_upper'],
            indicators['bb_lower'],
            current_price
        )
        indicators['bb_squeeze_ratio'] = bb_squeeze['bb_squeeze_ratio']
        indicators['bb_squeeze_active'] = bb_squeeze['bb_squeeze_active']


        # NEW: Weighted Buy Pressure
        indicators['weighted_buy_pressure'] = IndicatorsCalculator.calculate_weighted_buy_pressure(df, periods=7)

        atr = IndicatorsCalculator.atr(df, 14)
        indicators['atr'] = float(atr.iloc[-1] or 0)

        # VOLUME CALCULATION - Fixed to exclude incomplete candles
        df_complete = exclude_incomplete_candle_df(df)

        if len(df_complete) < 20:
            print(f"⚠️  Not enough complete candles for volume MA (need 20, got {len(df_complete)})")
            indicators['volume_ma20'] = 0
            indicators['volume_current'] = 0
            indicators['volume_ratio'] = 1.0
        else:
            vol_ma = IndicatorsCalculator.volume_ma(df_complete['volume'], 20)
            # Use the last COMPLETE candle's volume, not today's partial
            current_vol = float(df_complete['volume'].iloc[-1])
            indicators['volume_ma20'] = float(vol_ma.iloc[-1] or 0)
            indicators['volume_current'] = current_vol
            indicators['volume_ratio'] = IndicatorsCalculator.volume_ratio(current_vol, indicators['volume_ma20'])

        # Volume quality classification
        volume_quality = classify_volume_quality(indicators['volume_ratio'])
        indicators['volume_classification'] = volume_quality['classification']

        # Days since last volume spike - also use complete candles
        indicators['days_since_volume_spike'] = IndicatorsCalculator.days_since_volume_spike(df_complete, spike_threshold=1.5)

        # 14-day high/low for swing context
        last_14d = df.tail(14)
        indicators['high_14d'] = float(last_14d['high'].max())
        indicators['low_14d'] = float(last_14d['low'].min())

        # ATR as percentage of price
        if current_price > 0 and indicators['atr'] > 0:
            indicators['atr_percent'] = (indicators['atr'] / current_price) * 100
        else:
            indicators['atr_percent'] = 0.0

        support_levels, resistance_levels = IndicatorsCalculator.find_support_resistance(df, current_price, 30)

        # Only process first 2 levels
        for i in range(1, 3):  
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
    def calculate_ticker_indicators(ticker_dict: Dict, volume_ma20: float) -> Dict:
        try:
            indicators = {}

            current_price = float(ticker_dict.get('lastPrice', 0))
            price_change_24h = float(ticker_dict.get('priceChangePercent', 0))
            high_24h = float(ticker_dict.get('highPrice', 0))
            low_24h = float(ticker_dict.get('lowPrice', 0))
            volume_24h = float(ticker_dict.get('volume', 0))

            indicators['momentum_24h'] = price_change_24h

            range_24h = high_24h - low_24h
            if range_24h > 0:
                indicators['range_position_24h'] = (current_price - low_24h) / range_24h
            else:
                indicators['range_position_24h'] = 0.5

            if volume_ma20 > 0:
                indicators['volume_surge_24h'] = volume_24h / volume_ma20
            else:
                indicators['volume_surge_24h'] = 1.0

            return indicators

        except Exception as e:
            print(f"⚠️  Error calculating ticker indicators: {e}")
            return {
                'momentum_24h': 0.0,
                'range_position_24h': 0.0,
                'volume_surge_24h': 0.0
            }

    @staticmethod
    def calculate_btc_correlation(sol_df: pd.DataFrame, btc_df: pd.DataFrame, periods: int = 30) -> Dict:
        """
        Calculate BTC-SOL correlation and BTC trend for altcoin analysis
        Returns: BTC price, change, trend direction, correlation coefficient, and correlation strength
        """
        try:
            # Get BTC current data
            btc_price = float(btc_df['close'].iloc[-1])
            btc_open = float(btc_df['open'].iloc[0])  # First row = oldest (30 days ago)
            btc_price_change_30d = ((btc_price - btc_open) / btc_open * 100) if btc_open > 0 else 0

            # Calculate BTC trend using EMAs
            btc_ema20 = btc_df['close'].ewm(span=20, adjust=False).mean().iloc[-1] if len(btc_df) >= 20 else btc_price
            btc_ema50 = btc_df['close'].ewm(span=50, adjust=False).mean().iloc[-1] if len(btc_df) >= 50 else btc_price

            # Determine BTC trend
            if btc_ema20 > btc_ema50:
                btc_trend = "BULLISH"
            elif btc_ema20 < btc_ema50:
                btc_trend = "BEARISH"
            else:
                btc_trend = "NEUTRAL"

            # Calculate correlation
            sol_prices = sol_df['close'].tail(periods).tolist()
            btc_prices = btc_df['close'].tail(periods).tolist()

            correlation = IndicatorsCalculator.calculate_correlation(sol_prices, btc_prices)

            # Classify correlation strength
            if correlation >= 0.75:
                btc_correlation_strength = "STRONG"
            elif correlation >= 0.50:
                btc_correlation_strength = "MODERATE"
            elif correlation >= 0.25:
                btc_correlation_strength = "WEAK"
            else:
                btc_correlation_strength = "NONE"

            return {
                'btc_price': btc_price,
                'btc_price_change_30d': btc_price_change_30d,
                'btc_trend': btc_trend,
                'sol_btc_correlation': correlation,
                'btc_correlation_strength': btc_correlation_strength
            }

        except Exception as e:
            print(f"⚠️  Error calculating BTC correlation: {e}")
            return {
                'btc_price': 0.0,
                'btc_price_change_30d': 0.0,
                'btc_trend': 'UNKNOWN',
                'sol_btc_correlation': 0.8,  # Default assumption
                'btc_correlation_strength': 'UNKNOWN'
            }


if __name__ == "__main__":
    pass
