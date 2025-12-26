"""
Data manager for saving fetched data to PostgreSQL
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict
from sqlalchemy.dialects.postgresql import insert
from app.database.models.news import NewsModel
from app.database.models.indicators import IndicatorsModel
from app.database.models.candlestick import CandlestickModel, CandlestickIntradayModel, TickerModel
from app.database.config import get_db_session


class DataManager:
    def __init__(self):
        self.db = get_db_session()

    def __enter__(self):
        """Context manager entry - returns self for use in 'with' statements"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures db session is closed"""
        self.close()
        return False  # Don't suppress exceptions

    def save_ticker_db(self, df: pd.DataFrame) -> int:
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

        stmt = insert(CandlestickModel).values(records)
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

        stmt = insert(NewsModel).values(records)
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


    def save_indicators(self, timestamp: datetime, indicators: Dict) -> int:
        print(f"Saving indicators for {timestamp}...")

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
            'atr_percent': indicators.get('atr_percent'),
            'volume_ma20': indicators.get('volume_ma20'),
            'volume_current': indicators.get('volume_current'),
            'volume_ratio': indicators.get('volume_ratio'),
            'volume_classification': indicators.get('volume_classification'),
            'volume_trading_allowed': str(indicators.get('volume_trading_allowed', True)),
            'volume_confidence_multiplier': indicators.get('volume_confidence_multiplier'),
            'days_since_volume_spike': indicators.get('days_since_volume_spike'),
            'kijun_sen': indicators.get('kijun_sen'),
            'high_14d': indicators.get('high_14d'),
            'low_14d': indicators.get('low_14d'),
            'stoch_rsi': indicators.get('stoch_rsi'),
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

        stmt = insert(IndicatorsModel).values(record)
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
                'rsi_divergence_type': stmt.excluded.rsi_divergence_type,
                'rsi_divergence_strength': stmt.excluded.rsi_divergence_strength,
                'bb_upper': stmt.excluded.bb_upper,
                'bb_lower': stmt.excluded.bb_lower,
                'atr': stmt.excluded.atr,
                'atr_percent': stmt.excluded.atr_percent,
                'volume_ma20': stmt.excluded.volume_ma20,
                'volume_current': stmt.excluded.volume_current,
                'volume_ratio': stmt.excluded.volume_ratio,
                'volume_classification': stmt.excluded.volume_classification,
                'volume_trading_allowed': stmt.excluded.volume_trading_allowed,
                'volume_confidence_multiplier': stmt.excluded.volume_confidence_multiplier,
                'days_since_volume_spike': stmt.excluded.days_since_volume_spike,
                'kijun_sen': stmt.excluded.kijun_sen,
                'high_14d': stmt.excluded.high_14d,
                'low_14d': stmt.excluded.low_14d,
                'stoch_rsi': stmt.excluded.stoch_rsi,
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


    def save_technical_analysis(self, data: Dict) -> int:
        from app.database.models.analysis import TechnicalAnalyst
        
        record = {
            'recommendation': data.get('recommendation'),
            'confidence': data.get('confidence'),
            'confidence_breakdown': data.get('confidence_breakdown'),
            'timeframe': data.get('timeframe'),
            'entry_level': data.get('entry_level'),
            'stop_loss': data.get('stop_loss'),
            'take_profit': data.get('take_profit'),
            'key_signals': data.get('key_signals'),
            'reasoning': data.get('reasoning'),
            'recommendation_summary': data.get('recommendation_summary'),
            'watch_list': data.get('watch_list'),
            'thinking': data.get('thinking')
        }
        
        stmt = insert(TechnicalAnalyst).values(record)
        # stmt = stmt.on_conflict_do_update(
        #     index_elements=['created_at'],
        #     set_=record
        # )
        
        self.db.execute(stmt)
        self.db.commit()
        print(f"✅ Saved Technical Analysis {datetime.now()}")
        return 1




    def save_news_analysis(self, data: Dict) -> int:
        from app.database.models.analysis import NewsAnalyst
        
        record = {
            'overall_sentiment': data.get('overall_sentiment'),
            'sentiment_label': data.get('sentiment_label'),
            'confidence': data.get('confidence'),
            'key_events': data.get('key_events'),
            'all_recent_news': data.get('all_recent_news'),
            'event_summary': data.get('event_summary'),
            'risk_flags': data.get('risk_flags'),
            'stance': data.get('stance'),
            'suggested_timeframe': data.get('suggested_timeframe'),
            'recommendation_summary': data.get('recommendation_summary'),
            'what_to_watch': data.get('what_to_watch'),
            'invalidation': data.get('invalidation'),
            'thinking': data.get('thinking')
        }
        
        stmt = insert(NewsAnalyst).values(record)
        # stmt = stmt.on_conflict_do_update(
        #     index_elements=['timestamp'],
        #     set_=record
        # )
        
        self.db.execute(stmt)
        self.db.commit()
        print(f"✅ Saved News Analysis {datetime.now()}")
        return 1



    def save_reflection_analysis(self, data: Dict) -> int:
        from app.database.models.analysis import ReflectionAnalyst

        record = {
            'recommendation': data.get('recommendation'),
            'confidence': data.get('confidence'),
            'agreement_analysis': data.get('agreement_analysis'),
            'blind_spots': data.get('blind_spots'),
            'risk_assessment': data.get('risk_assessment'),
            'monitoring': data.get('monitoring'),
            'confidence_calculation': data.get('confidence_calculation'),
            'reasoning': data.get('reasoning'),
            'thinking': data.get('thinking')
        }

        stmt = insert(ReflectionAnalyst).values(record)
        # stmt = stmt.on_conflict_do_update(
        #     index_elements=['timestamp'],
        #     set_=record
        # )

        self.db.execute(stmt)
        self.db.commit()
        print(f"✅ Saved Reflection Analysis for {datetime.now()}")
        return 1



    def save_trader_decision(self, timestamp: datetime, data: Dict) -> int:
        from app.database.models.analysis import TraderAnalyst

        record = {
            'timestamp': timestamp,
            'decision': data.get('decision'),
            'confidence': data.get('confidence'),
            'reasoning': data.get('reasoning'),
            'agent_synthesis': data.get('agent_synthesis'),
            'execution_plan': data.get('execution_plan'),
            'risk_management': data.get('risk_management'),
            'thinking': data.get('thinking')
        }

        stmt = insert(TraderAnalyst).values(record)
        # stmt = stmt.on_conflict_do_update(
        #     index_elements=['timestamp'],
        #     set_=record
        # )

        self.db.execute(stmt)
        self.db.commit()
        print(f"✅ Saved Trader Decision for {timestamp}")
        return 1


    def close(self):
        if self.db:
            self.db.close()


