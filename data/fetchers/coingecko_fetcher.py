"""
CoinGecko API Fetcher for Solana Price Data
- Demo API (Free tier): 10,000 calls/month, requires API key
- Historical data: Up to 365 days on Demo API
- Rate limit: 30 calls/minute for Demo API
"""
import requests
import pandas as pd
import time
import os
import sys
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import DATA_DIR


class CoinGeckoFetcher:

    BASE_URL = "https://api.coingecko.com/api/v3"
    PRO_BASE_URL = "https://pro-api.coingecko.com/api/v3"


    def __init__(self, api_key: Optional[str] = None, is_pro: bool = False):
        self.api_key = api_key
        self.is_pro = is_pro
        self.base_url = self.PRO_BASE_URL if is_pro else self.BASE_URL

        self.headers = {}
        if api_key and is_pro:
            self.headers['x-cg-pro-api-key'] = api_key


    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}/{endpoint}"

        if params is None:
            params = {}

        if self.api_key and not self.is_pro:
            params['x_cg_demo_api_key'] = self.api_key

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            # Respect rate limits (Demo API: 30 calls/min, Pro API: higher)
            sleep_time = 2.0 if not self.is_pro else 0.5
            time.sleep(sleep_time)

            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ API Error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text[:200]}")
            return None


    def fetch_ohlcv_history(self, days: int = 180, vs_currency: str = "usd") -> pd.DataFrame:
        """
        Fetch historical price data with ALL important metrics

        NOTE: Using /market_chart endpoint instead of /ohlc because:
        - /ohlc has poor granularity (4 days per candle for 31+ days)
        - /market_chart gives daily data regardless of period
        - /market_chart includes price, volume, market_cap
        """
        print(f"📊 Fetching {days} days of Solana price data from CoinGecko...")

        # Use market_chart for daily granularity (NOT ohlc - poor granularity!)
        df = self.fetch_market_chart(days, vs_currency)

        if df.empty:
            print("❌ Failed to fetch price data")
            return pd.DataFrame()

        # Fetch current data to get additional important metrics
        current = self.fetch_current_price()

        # Add important metrics to the latest row
        if current and not df.empty:
            latest_idx = df.index[-1]
            df.loc[latest_idx, 'circulating_supply'] = current.get('circulating_supply', 0)
            df.loc[latest_idx, 'total_supply'] = current.get('total_supply', 0)
            df.loc[latest_idx, 'max_supply'] = current.get('max_supply', 0)
            df.loc[latest_idx, 'fdv'] = current.get('fdv', 0)
            df.loc[latest_idx, 'price_change_24h'] = current.get('change_24h', 0)

        print(f"✅ Fetched {len(df)} days of price data (daily granularity)")
        return df


    def fetch_market_chart(self, days: int = 180, vs_currency: str = "usd") -> pd.DataFrame:
        print(f"📈 Fetching {days} days of market chart data...")

        endpoint = "coins/solana/market_chart"
        params = {
            'vs_currency': vs_currency,
            'days': days,
            'interval': 'daily'
        }

        data = self._make_request(endpoint, params)

        if not data:
            print("❌ Failed to fetch market chart data")
            return pd.DataFrame()


        prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        volumes = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])
        market_caps = pd.DataFrame(data['market_caps'], columns=['timestamp', 'market_cap'])

        prices['timestamp'] = pd.to_datetime(prices['timestamp'], unit='ms')
        volumes['timestamp'] = pd.to_datetime(volumes['timestamp'], unit='ms')
        market_caps['timestamp'] = pd.to_datetime(market_caps['timestamp'], unit='ms')

        # Merge all data
        df = prices.merge(volumes, on='timestamp', how='left')
        df = df.merge(market_caps, on='timestamp', how='left')

        print(f"\n ------ market chart df:\n {df.head()}")

        print(f"✅ Fetched {len(df)} days of market data")
        return df

    def fetch_current_price(self) -> dict:
        print("💰 Fetching comprehensive Solana market data...")

        endpoint = "coins/solana"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'true',
            'community_data': 'false',
            'developer_data': 'false',
            'sparkline': 'false'
        }

        data = self._make_request(endpoint, params)

        if not data or 'market_data' not in data:
            print("❌ Failed to fetch market data")
            return {}

        market = data['market_data']
        current_price = market.get('current_price', {}).get('usd', 0)
        print(f"✅ Current SOL price: ${current_price:.2f}")

        return {
            'price': current_price,
            'market_cap': market.get('market_cap', {}).get('usd', 0),
            'fdv': market.get('fully_diluted_valuation', {}).get('usd', 0),
            'volume_24h': market.get('total_volume', {}).get('usd', 0),
            'circulating_supply': market.get('circulating_supply', 0),
            'total_supply': market.get('total_supply', 0),
            'max_supply': market.get('max_supply', 0),
            # Price changes
            'change_24h': market.get('price_change_percentage_24h', 0),
            'change_7d': market.get('price_change_percentage_7d', 0),
            'change_30d': market.get('price_change_percentage_30d', 0),
            # Additional metrics
            'ath': market.get('ath', {}).get('usd', 0),
            'ath_change_percentage': market.get('ath_change_percentage', {}).get('usd', 0),
            'atl': market.get('atl', {}).get('usd', 0),
            'market_cap_rank': data.get('market_cap_rank', 0),
            'last_updated': data.get('last_updated', '')
        }

    def save_to_csv(self, df: pd.DataFrame, filename: str):
        filepath = f"{DATA_DIR}/{filename}"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df.to_csv(filepath, index=False)
        print(f"💾 Saved data to {filepath}")


def main():
    api_key = os.getenv('COINGECKO_API_KEY')

    if not api_key:
        print("⚠️  COINGECKO_API_KEY not found in .env")
        return

    fetcher = CoinGeckoFetcher(api_key=api_key, is_pro=False)

    # Fetch up to 365 days of OHLCV data (Demo API limit)
    ohlcv_df = fetcher.fetch_ohlcv_history(days=295)
    if not ohlcv_df.empty:
        print(f"\n📊 OHLCV Data Sample:")
        print(ohlcv_df.head())
        print(f"\nDate range: {ohlcv_df['timestamp'].min()} to {ohlcv_df['timestamp'].max()}")

        fetcher.save_to_csv(ohlcv_df, "solana_daily_price.csv")

    # Fetch current price and ALL metrics
    current = fetcher.fetch_current_price()
    if current:
        print(f"\n💰 Current Market Data:")
        print(f"  Price: ${current['price']:.2f}")
        print(f"  Market Cap: ${current['market_cap']:,.0f}")
        print(f"  FDV (Fully Diluted Valuation): ${current['fdv']:,.0f}")
        print(f"  24h Volume: ${current['volume_24h']:,.0f}")
        print(f"  Circulating Supply: {current['circulating_supply']:,.0f} SOL")
        print(f"  Total Supply: {current['total_supply']:,.0f} SOL")
        print(f"  Max Supply: {current['max_supply'] if current['max_supply'] else 'Unlimited'}")
        print(f"  24h Change: {current['change_24h']:.2f}%")
        print(f"  7d Change: {current['change_7d']:.2f}%")
        print(f"  30d Change: {current['change_30d']:.2f}%")
        print(f"  Market Cap Rank: #{current['market_cap_rank']}")


if __name__ == "__main__":
    main()
