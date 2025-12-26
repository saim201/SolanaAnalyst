
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


class BinanceFetcher:
    BASE_URL = "https://api.binance.com/api/v3"
    SYMBOL = "SOLUSDT"  
    
    def __init__(self):
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: dict = None) -> Optional[list]:
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Binance API Error: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Response: {e.response.text[:200]}")
            return None
    

    def fetch_ticker24h(self) -> pd.DataFrame:
        params = {
            'symbol': self.SYMBOL
        }

        try:
            ticker = self._make_request('ticker/24hr', params)
            if not ticker:
                print("No ticker data received")
                return pd.DataFrame()

            record = {
                'lastPrice': float(ticker.get('lastPrice', 0)),
                'priceChangePercent': float(ticker.get('priceChangePercent', 0)),
                'openPrice': float(ticker.get('openPrice', 0)),
                'highPrice': float(ticker.get('highPrice', 0)),
                'lowPrice': float(ticker.get('lowPrice', 0)),
                'volume': float(ticker.get('volume', 0)),
                'quoteVolume': float(ticker.get('quoteVolume', 0)),
                'timestamp': datetime.now()
            }

            df = pd.DataFrame([record])
            return df
        except Exception as e:
            print(f"Error parsing ticker data: {str(e)}")
            return pd.DataFrame()  


    def fetch_and_save_ticker_db(self) -> bool:
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from database.data_manager import DataManager

            df = self.fetch_ticker24h()

            if df.empty:
                print("Failed ticker 24h fetching")
                return False

            with DataManager() as manager:
                manager.save_ticker_db(df)
            return True

        except Exception as e:
            print(f"Error saving ticker data to DB: {str(e)}")
            return False



    def fetch_klines(self, interval: str = '1d', limit: int = 90) -> pd.DataFrame:
        params = {
            'symbol': self.SYMBOL,
            'interval': interval,
            'limit': limit
        }

        try:
            klines = self._make_request('klines', params)

            if not klines:
                print("No klines data received")
                return pd.DataFrame()

            records = []
            for kline in klines:
                record = {
                    'open_time': datetime.fromtimestamp(kline[0] / 1000),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),                  
                    'close_time': datetime.fromtimestamp(kline[6] / 1000),
                    'quote_volume': float(kline[7]),
                    'num_trades': int(kline[8]),
                    'taker_buy_base': float(kline[9]),
                    'taker_buy_quote': float(kline[10]),
                }
                records.append(record)

            df = pd.DataFrame(records)
            print(f"Fetched {len(df)} candles - with {interval} interval")
            print(f"candles data: \n {df}" )
            return df

        except Exception as e:
            print(f"Error parsing klines: {str(e)}")
            return pd.DataFrame()
    


    def fetch_and_save_klines_db(self, interval: str = '1d', limit: int = 90) -> bool:
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from database.data_manager import DataManager

            df = self.fetch_klines(interval=interval, limit=limit)

            if df.empty:
                print("Failed klines fetching")
                return False

            with DataManager() as manager:
                if limit == 6:
                    manager.save_candlestickIntraday_db(df)
                else:
                    manager.save_candlestick_db(df)
            return True

        except Exception as e:
            print(f"Error saving klines data to DB: {str(e)}")
            return False


def main():
    
    fetcher = BinanceFetcher()
    
    # 90 days of daily candles (one-time setup):
    # fetcher.fetch_klines(interval='1d', limit=90)

    # Today's 4h candles (3x daily):
    # fetcher.fetch_klines(interval='4h', limit=6)


    # fetcher.fetch_and_save_klines_db(interval='4h', limit=6)
    # fetcher.fetch_and_save_klines_db()

    fetcher.fetch_and_save_ticker_db()

    


if __name__ == "__main__":
    main()
