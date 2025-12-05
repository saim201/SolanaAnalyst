"""
Data manager for saving fetched data to PostgreSQL
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict
from sqlalchemy.dialects.postgresql import insert
from database.models import NewsData, CandlestickData, TickerModel, CandlestickIntradayModel
from database.config import get_db_session


class DataManager:
    def __init__(self):
        self.db = get_db_session()

    def save_tikcer_db(self, df: pd.DataFrame) -> int:
        records = []
        for _, row in df.iterrows():
            record = {
                'lastPrice': float(row['lastPrice']),
                'priceChangePercent': float(row['priceChangePercent']),
                'openPrice': float(row['openPrice']),
                'highPrice': float(row['highPrice']),
                'lowPrice': float(row['lowPrice']),
                'volume': row['volume'],
                'quoteVolume': int(row['quoteVolume']),
                'timestamp': row['timestamp']
            }
            records.append(record)

        stmt = insert(TickerModel).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['timestamp'],
            set_={
                'lastPrice': stmt.excluded.lastPrice,
                'priceChangePercent': stmt.excluded.priceChangePercent,
                'openPrice': stmt.excluded.openPrice,
                'highPrice': stmt.excluded.highPrice,
                'lowPrice': stmt.excluded.lowPrice,
                'volume': stmt.excluded.volume,
                'quoteVolume': stmt.excluded.quoteVolume
            }
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f"Saved {len(records)} records to databse")
        return len(records)


    def save_candlestick_db(self, df: pd.DataFrame) -> int:
        records = []
        for _, row in df.iterrows():
            record = {
                'open_time': row['open_time'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'close_time': row['close_time'],
                'volume': int(row['volume']),
                'quote_volume': int(row['quote_volume']),
                'num_trades': int(row['num_trades']),
                'taker_buy_base': int(row['taker_buy_base']),
                'taker_buy_quote': int(row['taker_buy_quote']),
            }
            records.append(record)

        stmt = insert(CandlestickData).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['open_time'],
            set_={
                'open': stmt.excluded.open,
                'high': stmt.excluded.high,
                'low': stmt.excluded.low,
                'close': stmt.excluded.close,
                'volume': stmt.excluded.volume,
                'quote_volume': stmt.excluded.quote_volume,
                'num_trades': stmt.excluded.num_trades,
                'taker_buy_base': stmt.excluded.taker_buy_base,
                'taker_buy_quote': stmt.excluded.taker_buy_quote,
                'close_time': stmt.excluded.close_time,
            }
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f"Saved {len(records)} records to databse")
        return len(records)


    def save_candlestickIntraday_db(self, df: pd.DataFrame) -> int:
        records = []
        for _, row in df.iterrows():
            record = {
                'open_time': row['open_time'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'close_time': row['close_time'],
                'volume': int(row['volume']),
                'quote_volume': int(row['quote_volume']),
                'num_trades': int(row['num_trades']),
                'taker_buy_base': int(row['taker_buy_base']),
                'taker_buy_quote': int(row['taker_buy_quote']),
            }
            records.append(record)

        stmt = insert(CandlestickIntradayModel).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['open_time'],
            set_={
                'open': stmt.excluded.open,
                'high': stmt.excluded.high,
                'low': stmt.excluded.low,
                'close': stmt.excluded.close,
                'volume': stmt.excluded.volume,
                'quote_volume': stmt.excluded.quote_volume,
                'num_trades': stmt.excluded.num_trades,
                'taker_buy_base': stmt.excluded.taker_buy_base,
                'taker_buy_quote': stmt.excluded.taker_buy_quote,
                'close_time': stmt.excluded.close_time,
            }
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f"Saved {len(records)} records to databse")
        return len(records)


    def save_news_data(self, articles: List[Dict]) -> int:
        records = []
        for article in articles:
            published_at = article['published_at']
            if isinstance(published_at, str):
                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))


            sentiment = article.get('sentiment')
            if sentiment is None or (isinstance(sentiment, float) and pd.isna(sentiment)):
                sentiment = None

            record = {
                'title': article['title'][:500],
                'url': article['url'][:1000],
                'source': article['source'][:200],
                'published_at': published_at,
                'content': article.get('content'),
                'sentiment': sentiment,
                'priority': article.get('priority'),
            }
            records.append(record)

        stmt = insert(NewsData).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['url'],
            set_={
                'title': stmt.excluded.title,
                'source': stmt.excluded.source,
                'published_at': stmt.excluded.published_at,
                'content': stmt.excluded.content,
                'sentiment': stmt.excluded.sentiment,
                'priority': stmt.excluded.priority,
            }
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f"✅ Saved {len(records)} news articles")
        return len(records)

    def get_latest_news_date(self):
        result = self.db.query(NewsData).order_by(NewsData.published_at.desc()).first()
        return result.published_at if result else None

    def save_indicators(self, timestamp: datetime, indicators: Dict) -> int:
        print(f"💾 Saving indicators for {timestamp}...")

        from database.models import IndicatorsData

        record = {
            'timestamp': timestamp,
            'ema20': indicators.get('ema20'),
            'ema50': indicators.get('ema50'),
            'ema200': indicators.get('ema200'),
            'macd_line': indicators.get('macd_line'),
            'macd_signal': indicators.get('macd_signal'),
            'macd_histogram': indicators.get('macd_histogram'),
            'rsi14': indicators.get('rsi14'),
            'rsi_divergence_type': indicators.get('rsi_divergence_type'),
            'rsi_divergence_strength': indicators.get('rsi_divergence_strength'),
            'bb_upper': indicators.get('bb_upper'),
            'bb_lower': indicators.get('bb_lower'),
            'atr': indicators.get('atr'),
            'volume_ma20': indicators.get('volume_ma20'),
            'volume_current': indicators.get('volume_current'),
            'volume_ratio': indicators.get('volume_ratio'),
            'support1': indicators.get('support1'),
            'support1_percent': indicators.get('support1_percent'),
            'support2': indicators.get('support2'),
            'support2_percent': indicators.get('support2_percent'),
            'resistance1': indicators.get('resistance1'),
            'resistance1_percent': indicators.get('resistance1_percent'),
            'resistance2': indicators.get('resistance2'),
            'resistance2_percent': indicators.get('resistance2_percent'),
            'fib_level_382': indicators.get('fib_level_382'),
            'fib_level_618': indicators.get('fib_level_618'),
            'pivot_weekly': indicators.get('pivot_weekly'),
            'momentum_24h': indicators.get('momentum_24h'),
            'range_position_24h': indicators.get('range_position_24h'),
            'volume_surge_24h': indicators.get('volume_surge_24h'),
        }

        stmt = insert(IndicatorsData).values(record)
        stmt = stmt.on_conflict_do_update(
            index_elements=['timestamp'],
            set_={
                'ema20': stmt.excluded.ema20,
                'ema50': stmt.excluded.ema50,
                'ema200': stmt.excluded.ema200,
                'macd_line': stmt.excluded.macd_line,
                'macd_signal': stmt.excluded.macd_signal,
                'macd_histogram': stmt.excluded.macd_histogram,
                'rsi14': stmt.excluded.rsi14,
                'rsi_divergence_type':stmt.excluded.rsi_divergence_type ,
                'rsi_divergence_strength': stmt.excluded.rsi_divergence_strength,
                'bb_upper': stmt.excluded.bb_upper,
                'bb_lower': stmt.excluded.bb_lower,
                'atr': stmt.excluded.atr,
                'volume_ma20': stmt.excluded.volume_ma20,
                'volume_current': stmt.excluded.volume_current,
                'volume_ratio': stmt.excluded.volume_ratio,
                'support1': stmt.excluded.support1,
                'support1_percent': stmt.excluded.support1_percent,
                'support2': stmt.excluded.support2,
                'support2_percent': stmt.excluded.support2_percent,
                'resistance1': stmt.excluded.resistance1,
                'resistance1_percent': stmt.excluded.resistance1_percent,
                'resistance2': stmt.excluded.resistance2,
                'resistance2_percent': stmt.excluded.resistance2_percent,
                'fib_level_382': stmt.excluded.fib_level_382,
                'fib_level_618': stmt.excluded.fib_level_618,
                'pivot_weekly': stmt.excluded.pivot_weekly,
                'momentum_24h': stmt.excluded.momentum_24h,
                'range_position_24h': stmt.excluded.range_position_24h,
                'volume_surge_24h': stmt.excluded.volume_surge_24h,
            }
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f"✅ Saved indicators for {timestamp}")
        return 1

    def close(self):
        if self.db:
            self.db.close()
