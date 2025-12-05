import sys
import os
from datetime import datetime
import pandas as pd

# Add backend directory to path so imports work when running directly
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.data.fetchers.binance_fetcher import BinanceFetcher
from app.data.fetchers.rss_news_fetcher import RSSNewsFetcher
from app.data.indicators import IndicatorsProcessor
from app.database.config import get_db_session
from app.database.data_manager import DataManager
from app.database.models import CandlestickData, CandlestickIntradayModel, TickerModel


class RefreshManager:
    @staticmethod
    def refresh_all_data():
        print(f"Refreshing data - {datetime.now().isoformat()}")

        success_count = 0
        total_sources = 4

        binance_success = RefreshManager._fetch_candlestick_data()
        if binance_success:
            success_count += 1

        tickle_success = RefreshManager._fetch_ticker_data()
        if tickle_success:
            success_count += 1

        news_success = RefreshManager._fetch_news_data()
        if news_success:
            success_count += 1


        
        indicators_success = RefreshManager._calculate_and_save_indicators()
        if indicators_success:
            success_count += 1


        print(f"Refresh complete: {success_count}/{total_sources} sources updated")
        return success_count == total_sources
    

    @staticmethod
    def _fetch_ticker_data() -> bool:
        try:
            binance_fetcher = BinanceFetcher()
            if binance_fetcher.fetch_and_save_ticker_db():
                return True
            return False
        except Exception as e:
            print(f"Tickle 24h fetch error: {str(e)}")
            return False


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
    def _fetch_news_data() -> bool:
        try:
            news_fetcher = RSSNewsFetcher()
            if news_fetcher.fetch_and_save_to_db():
                return True
            return False
        except Exception as e:
            print(f"News fetch error: {str(e)}")
            return False
    


    @staticmethod
    def _calculate_and_save_indicators() -> bool:
        try:
            db = get_db_session()

            daily_candles = db.query(CandlestickData).order_by(
                CandlestickData.open_time.desc()
            ).limit(90).all()

            ticker_data = db.query(TickerModel).order_by(
                TickerModel.timestamp.desc()
            ).first()


            db.close()  

            daily_candles = sorted(daily_candles, key=lambda x: x.open_time)

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

            ticker_indicators = {}
            try:
                if ticker_data:
                    volume_ma20 = daily_indicators.get('volume_ma20', 1.0)
                    ticker_dict = {
                        'lastPrice': ticker_data.lastPrice,
                        'priceChangePercent': ticker_data.priceChangePercent,
                        'highPrice': ticker_data.highPrice,
                        'lowPrice': ticker_data.lowPrice,
                        'volume': ticker_data.volume,
                    }
                    ticker_indicators = IndicatorsProcessor.calculate_ticker_indicators(ticker_dict, volume_ma20)
            except Exception as e:
                print(f"Ticker indicators calculation warning: {str(e)}")

            combined_indicators = {**daily_indicators, **ticker_indicators}

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
    
    RefreshManager.refresh_all_data()
