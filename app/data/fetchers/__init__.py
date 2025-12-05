"""
Data fetchers package - external data sources.
"""
from app.data.fetchers.binance_fetcher import BinanceFetcher
from app.data.fetchers.rss_news_fetcher import RSSNewsFetcher

__all__ = [
    "BinanceFetcher",
    "RSSNewsFetcher",
]
