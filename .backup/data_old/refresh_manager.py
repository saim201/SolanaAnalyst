import sys
import os
from datetime import datetime
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetchers.binance_fetcher import BinanceFetcher
from data.fetchers.rss_news_fetcher import RSSNewsFetcher
from data.indicators import IndicatorsProcessor
from database.config import get_db_session
from database.data_manager import DataManager
from database.models import CandlestickData, CandlestickIntradayModel


class RefreshManager:
    @staticmethod
    def refresh_all_data(days: int = 1):
        print(f"Refreshing data for {days} day(s) - {datetime.now().isoformat()}")

        success_count = 0
        total_sources = 2

        binance_success = RefreshManager._fetch_candlestick_data()
        if binance_success:
            success_count += 1

        # news_success = RefreshManager._fetch_news_data(days)
        # if news_success:
        #     success_count += 1

        indicators_success = RefreshManager._calculate_and_save_indicators()
        if indicators_success:
            success_count += 1

        print(f"Refresh complete: {success_count}/{total_sources} sources updated")
        return success_count == total_sources
    
    @staticmethod
    def _fetch_candlestick_data() -> bool:
        try:
            binance_fetcher = BinanceFetcher()

            daily_success = binance_fetcher.fetch_and_save_klines_db(interval='1d', limit=90)

            intraday_success = binance_fetcher.fetch_and_save_klines_db(interval='4h', limit=6)

            return daily_success and intraday_success
        except Exception as e:
            print(f"Candlestick fetch error: {str(e)}")
            return False
    
    @staticmethod
    def _fetch_news_data(days: int) -> bool:
        try:
            news_fetcher = RSSNewsFetcher()
            if news_fetcher.fetch_and_save_to_db(days=days):
                return True
            return False
        except Exception as e:
            print(f"News fetch error: {str(e)}")
            return False
    
    @staticmethod
    def _calculate_and_save_indicators() -> bool:
        # 63 indicators (56 daily + 7 4h)
        try:
            db = get_db_session()

            daily_candles = db.query(CandlestickData).order_by(
                CandlestickData.open_time.desc()
            ).limit(90).all()

            intraday_candles = db.query(CandlestickIntradayModel).order_by(
                CandlestickIntradayModel.open_time.desc()
            ).limit(6).all()

            db.close()

            daily_candles = sorted(daily_candles, key=lambda x: x.open_time)
            intraday_candles = sorted(intraday_candles, key=lambda x: x.open_time)

            daily_df = pd.DataFrame([{
                'open': c.open,
                'high': c.high,
                'low': c.low,
                'close': c.close,
                'volume': c.volume,
                'taker_buy_base': c.taker_buy_base,
                'open_time': c.open_time
            } for c in daily_candles])

            daily_indicators = IndicatorsProcessor.calculate_all_indicators(daily_df)

            if not daily_indicators:
                return False

            intraday_indicators = {}
            if intraday_candles and len(intraday_candles) >= 3:
                intraday_df = pd.DataFrame([{
                    'open': c.open,
                    'high': c.high,
                    'low': c.low,
                    'close': c.close,
                    'volume': c.volume,
                    'taker_buy_base': c.taker_buy_base,
                    'open_time': c.open_time
                } for c in intraday_candles])

                intraday_indicators = IndicatorsProcessor.calculate_intraday_indicators(intraday_df)

            combined_indicators = {**daily_indicators, **intraday_indicators}

            manager = DataManager()
            # Use the latest candle's timestamp instead of current time to avoid duplicates
            indicator_timestamp = daily_candles[-1].open_time if daily_candles else datetime.now()
            manager.save_indicators(indicator_timestamp, combined_indicators)
            manager.close()
            return True

        except Exception as e:
            import traceback
            print(f"Indicator calculation error: {str(e)}")
            traceback.print_exc()
            return False


if __name__ == "__main__":
    from datetime import date
    
    start_date = date(2025, 1, 31)
    today = date.today()
    total_days = (today - start_date).days
    
    RefreshManager.refresh_all_data(days=total_days)
