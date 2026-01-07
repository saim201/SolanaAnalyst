# Data manager for saving fetched data to PostgreSQL

import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from sqlalchemy.dialects.postgresql import insert
from app.database.models.news import NewsModel
from app.database.models.cfgi import CFGIData
from app.database.models.indicators import IndicatorsModel
from app.database.models.candlestick import CandlestickModel, CandlestickIntradayModel, TickerModel, BTCTickerModel, BTCCandlestickModel
from app.database.config import get_db_session


CFGI_CACHE_HOURS = 4


class DataManager:
    def __init__(self):
        self.db = get_db_session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
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
                'volume': float(row['volume']),
                'quoteVolume': float(row['quoteVolume']),
                'timestamp': row['timestamp']
            }
            records.append(record)

        # Ticker is time-series data - just insert new records, skip duplicates
        stmt = insert(TickerModel).values(records)
        stmt = stmt.on_conflict_do_nothing(index_elements=['timestamp'])

        self.db.execute(stmt)
        self.db.commit()

        print(f"Saved {len(records)} SOL ticker data to databse")
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
                'close_time': stmt.excluded.close_time,
                'volume': stmt.excluded.volume,
                'quote_volume': stmt.excluded.quote_volume,
                'num_trades': stmt.excluded.num_trades,
                'taker_buy_base': stmt.excluded.taker_buy_base,
                'taker_buy_quote': stmt.excluded.taker_buy_quote,
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
                'close_time': stmt.excluded.close_time,
                'volume': stmt.excluded.volume,
                'quote_volume': stmt.excluded.quote_volume,
                'num_trades': stmt.excluded.num_trades,
                'taker_buy_base': stmt.excluded.taker_buy_base,
                'taker_buy_quote': stmt.excluded.taker_buy_quote,
            }
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f"Saved {len(records)} records to databse")
        return len(records)


    def save_btc_ticker_db(self, df: pd.DataFrame) -> int:
        records = []
        for _, row in df.iterrows():
            record = {
                'lastPrice': float(row['lastPrice']),
                'priceChangePercent': float(row['priceChangePercent']),
                'openPrice': float(row['openPrice']),
                'highPrice': float(row['highPrice']),
                'lowPrice': float(row['lowPrice']),
                'volume': float(row['volume']),
                'quoteVolume': float(row['quoteVolume']),
                'timestamp': row['timestamp']
            }
            records.append(record)

        # BTC Ticker is time-series data - just insert new records, skip duplicates
        stmt = insert(BTCTickerModel).values(records)
        stmt = stmt.on_conflict_do_nothing(index_elements=['timestamp'])

        self.db.execute(stmt)
        self.db.commit()

        print(f" Saved {len(records)} BTC ticker records to database")
        return len(records)


    def save_btc_candlestick_db(self, df: pd.DataFrame) -> int:
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

        stmt = insert(BTCCandlestickModel).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['open_time'],
            set_={
                'open': stmt.excluded.open,
                'high': stmt.excluded.high,
                'low': stmt.excluded.low,
                'close': stmt.excluded.close,
                'close_time': stmt.excluded.close_time,
                'volume': stmt.excluded.volume,
                'quote_volume': stmt.excluded.quote_volume,
                'num_trades': stmt.excluded.num_trades,
                'taker_buy_base': stmt.excluded.taker_buy_base,
                'taker_buy_quote': stmt.excluded.taker_buy_quote,
            }
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f" Saved {len(records)} BTC candlestick records to database")
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

        record = {
            'timestamp': timestamp,
            # Trend
            'ema20': indicators.get('ema20'),
            'ema50': indicators.get('ema50'),
            'high_14d': indicators.get('high_14d'),
            'low_14d': indicators.get('low_14d'),
            # Momentum
            'macd_line': indicators.get('macd_line'),
            'macd_signal': indicators.get('macd_signal'),
            'macd_histogram': indicators.get('macd_histogram'),
            'rsi14': indicators.get('rsi14'),
            'rsi_divergence_type': indicators.get('rsi_divergence_type'),
            'rsi_divergence_strength': indicators.get('rsi_divergence_strength'),
            # Volatility
            'bb_upper': indicators.get('bb_upper'),
            'bb_lower': indicators.get('bb_lower'),
            'bb_squeeze_ratio': indicators.get('bb_squeeze_ratio'),
            'bb_squeeze_active': str(indicators.get('bb_squeeze_active', False)),
            'atr': indicators.get('atr'),
            'atr_percent': indicators.get('atr_percent'),
            # Volume
            'volume_ma20': indicators.get('volume_ma20'),
            'volume_current': indicators.get('volume_current'),
            'volume_ratio': indicators.get('volume_ratio'),
            'volume_classification': indicators.get('volume_classification'),
            'weighted_buy_pressure': indicators.get('weighted_buy_pressure'),
            'days_since_volume_spike': indicators.get('days_since_volume_spike'),
            # Support/Resistance
            'support1': indicators.get('support1'),
            'support1_percent': indicators.get('support1_percent'),
            'support2': indicators.get('support2'),
            'support2_percent': indicators.get('support2_percent'),
            'resistance1': indicators.get('resistance1'),
            'resistance1_percent': indicators.get('resistance1_percent'),
            'resistance2': indicators.get('resistance2'),
            'resistance2_percent': indicators.get('resistance2_percent'),
            # BTC Correlation
            'btc_price_change_30d': indicators.get('btc_price_change_30d'),
            'btc_trend': indicators.get('btc_trend'),
            'sol_btc_correlation': indicators.get('sol_btc_correlation'),
        }

        stmt = insert(IndicatorsModel).values(record)
        stmt = stmt.on_conflict_do_update(
            index_elements=['timestamp'],
            set_={k: v for k, v in record.items() if k != 'timestamp'}
        )

        self.db.execute(stmt)
        self.db.commit()

        print(f"✅ Saved indicators to db for {timestamp}")
        return 1


    def save_technical_analysis(self, data: Dict) -> int:
        from app.database.models.analysis import TechnicalAnalyst

        record = TechnicalAnalyst(
            timestamp=data.get('timestamp'),
            recommendation_signal=data.get('recommendation_signal'),
            confidence=data.get('confidence'),
            market_condition=data.get('market_condition'),
            thinking=data.get('thinking'),
            analysis=data.get('analysis'),
            trade_setup=data.get('trade_setup'),
            action_plan=data.get('action_plan'),
            watch_list=data.get('watch_list'),
            invalidation=data.get('invalidation'),
            confidence_reasoning=data.get('confidence_reasoning'),
        )

        self.db.add(record)
        self.db.commit()
        print(f"✅ Saved Technical Analysis in db {datetime.now()}")
        return 1




    def save_sentiment_analysis(self, data: Dict) -> int:
        from app.database.models.analysis import SentimentAnalyst

        record = {
            'timestamp': data.get('timestamp'),
            'recommendation_signal': data.get('recommendation_signal'),
            'market_condition': data.get('market_condition'),
            'confidence': data.get('confidence'),
            'market_fear_greed': data.get('market_fear_greed'),
            'news_sentiment': data.get('news_sentiment'),
            'combined_sentiment': data.get('combined_sentiment'),
            'positive_catalysts': data.get('positive_catalysts'),
            'negative_risks': data.get('negative_risks'),
            'key_events': data.get('key_events'),
            'risk_flags': data.get('risk_flags'),
            'what_to_watch': data.get('what_to_watch'),
            'invalidation': data.get('invalidation'),
            'suggested_timeframe': data.get('suggested_timeframe'),
            'thinking': data.get('thinking')
        }

        stmt = insert(SentimentAnalyst).values(record)

        self.db.execute(stmt)
        self.db.commit()
        print(f"✅ Saved Sentiment Analysis {datetime.now()}")
        return 1



    def save_reflection_analysis(self, data: Dict) -> int:
        from app.database.models.analysis import ReflectionAnalyst

        record = {
            'timestamp': data.get('timestamp'),
            'recommendation_signal': data.get('recommendation_signal'),
            'market_condition': data.get('market_condition'),
            'confidence': data.get('confidence'),
            'agent_alignment': data.get('agent_alignment'),
            'blind_spots': data.get('blind_spots'),
            'primary_risk': data.get('primary_risk'),
            'monitoring': data.get('monitoring'),
            'calculated_metrics': data.get('calculated_metrics'),
            'final_reasoning': data.get('final_reasoning'),
            'thinking': data.get('thinking')
        }

        stmt = insert(ReflectionAnalyst).values(record)

        self.db.execute(stmt)
        self.db.commit()
        print(f"✅ Saved Reflection Analysis for {datetime.now()}")
        return 1



    def save_trader_decision(self, data: Dict) -> int:
        from app.database.models.analysis import TraderAnalyst

        record = {
            'timestamp': data.get('timestamp'),
            'recommendation_signal': data.get('recommendation_signal'),
            'market_condition': data.get('market_condition'),
            'confidence': data.get('confidence'),
            'final_verdict': data.get('final_verdict'),
            'trade_setup': data.get('trade_setup'),
            'action_plan': data.get('action_plan'),
            'what_to_monitor': data.get('what_to_monitor'),
            'risk_assessment': data.get('risk_assessment'),
            'thinking': data.get('thinking')
        }

        stmt = insert(TraderAnalyst).values(record)

        self.db.execute(stmt)
        self.db.commit()
        print(f"✅ Saved Trader Decision for {data.get('timestamp')}")
        return 1


    def get_latest_cfgi(self):
        return self.db.query(CFGIData).order_by(CFGIData.fetched_at.desc()).first()

    def should_fetch_cfgi(self) -> bool:
        latest = self.get_latest_cfgi()
        if latest is None:
            return True
        cache_age = datetime.now(timezone.utc) - latest.fetched_at.replace(tzinfo=timezone.utc)
        return cache_age > timedelta(hours=CFGI_CACHE_HOURS)

    def save_cfgi_data(self, data) -> None:
        cfgi_record = CFGIData(
            score=data.score,
            classification=data.classification,
            social=data.social,
            whales=data.whales,
            trends=data.trends,
            sol_price=data.price,
            cfgi_timestamp=data.timestamp,
            fetched_at=datetime.now(timezone.utc)
        )
        self.db.add(cfgi_record)
        self.db.commit()
        print(f" Saved CFGI data: {data.score} ({data.classification})")

    def get_cfgi_with_cache(self):
        if self.should_fetch_cfgi():
            print("CFGI cache stale, fetching fresh data...")
            try:
                from app.data.fetchers.cfgi_fetcher import CFGIFetcher
                fetcher = CFGIFetcher()
                fresh_data = fetcher.fetch()

                if fresh_data:
                    self.save_cfgi_data(fresh_data)
                    return self.get_latest_cfgi().to_dict()
                else:
                    print(" Fresh fetch failed, using stale cache if available")
                    latest = self.get_latest_cfgi()
                    return latest.to_dict() if latest else None
            except Exception as e:
                print(f" CFGI fetch error: {e}")
                latest = self.get_latest_cfgi()
                return latest.to_dict() if latest else None
        else:
            print(" Using cached CFGI data (less than 4 hours old)")
            latest = self.get_latest_cfgi()
            return latest.to_dict() if latest else None

    def close(self):
        if self.db:
            self.db.close()


