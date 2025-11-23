"""
Google News RSS Fetcher for Crypto News
"""
import feedparser
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import DATA_DIR


class GoogleNewsFetcher:
    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self):
        pass

    def fetch_news(self, query: str = "Solana cryptocurrency", days_back: int = 7) -> List[Dict]:
        print(f"📰 Fetching news from Google News ({days_back} days)...")

        params = f"?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
        url = f"{self.BASE_URL}{params}"

        try:
            feed = feedparser.parse(url)

            if not feed.entries:
                print("⚠️  No news found")
                return []

            articles = []
            cutoff_date = datetime.now() - timedelta(days=days_back)

            for entry in feed.entries[:50]:
                pub_date = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now()

                if pub_date < cutoff_date:
                    continue

                article = {
                    'title': entry.title,
                    'url': entry.link,
                    'source': entry.source.title if hasattr(entry, 'source') else 'Google News',
                    'published_at': pub_date.isoformat(),
                    'content': entry.summary if hasattr(entry, 'summary') else entry.title,
                    'sentiment': self._analyze_sentiment(entry.title)
                }
                articles.append(article)

            print(f"✅ Fetched {len(articles)} news articles")
            return articles

        except Exception as e:
            print(f"❌ Error fetching news: {e}")
            return []

    def _analyze_sentiment(self, title: str) -> str:
        title_lower = title.lower()

        positive_words = ['surge', 'soars', 'rally', 'gains', 'growth', 'bullish', 'breakthrough', 'upgrade', 'launch']
        negative_words = ['crash', 'plunge', 'fall', 'drop', 'decline', 'bearish', 'hack', 'exploit', 'fraud']

        pos_count = sum(1 for word in positive_words if word in title_lower)
        neg_count = sum(1 for word in negative_words if word in title_lower)

        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        return 'neutral'

    def save_to_csv(self, articles: List[Dict], filename: str = "solana_news.csv"):
        os.makedirs(DATA_DIR, exist_ok=True)
        filepath = f"{DATA_DIR}/{filename}"

        with open(filepath, 'w') as f:
            for article in articles:
                line = f"{article['published_at']}\t{article['title']}\t{article['source']}\t{article['sentiment']}\t{article['url']}\n"
                f.write(line)

        print(f"💾 Saved {len(articles)} articles to {filepath}")


def main():
    print("Testing Google News Fetcher...\n")

    fetcher = GoogleNewsFetcher()

    # Test 1: Fetch recent news
    print("=" * 80)
    print("Test 1: Fetching last 7 days of news")
    print("=" * 80)
    articles = fetcher.fetch_news(query="Solana cryptocurrency", days_back=7)

    if articles:
        print(f"\n📰 Sample (first 3 articles):")
        for i, article in enumerate(articles[:3], 1):
            print(f"\n{i}. {article['title']}")
            print(f"   Sentiment: {article['sentiment']}")
            print(f"   Source: {article['source']}")
            print(f"   Date: {article['published_at'][:10]}")

    # Test 2: Save to CSV
    print("\n" + "=" * 80)
    print("Test 2: Saving to CSV")
    print("=" * 80)
    if articles:
        fetcher.save_to_csv(articles, "test_news.csv")


if __name__ == "__main__":
    main()
