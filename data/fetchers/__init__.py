"""Data fetchers for Solana trading agent"""
from .coingecko_fetcher import CoinGeckoFetcher
from .solscan_fetcher import SolscanFetcher
from .googlenews_fetcher import GoogleNewsFetcher

__all__ = ['CoinGeckoFetcher', 'SolscanFetcher', 'GoogleNewsFetcher']
