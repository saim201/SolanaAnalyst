import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import get_db_session
from database.models import PriceData, TransactionData, NewsData


class DataQuery:
    def __init__(self):
        self.db = get_db_session()

    def get_price_data(self, days: int = 30) -> str:
        cutoff = datetime.now() - timedelta(days=days)
        prices = self.db.query(PriceData).filter(
            PriceData.timestamp >= cutoff
        ).order_by(PriceData.timestamp.desc()).all()

        if not prices:
            return "No price data available"

        latest = prices[0]
        price_list = sorted(prices, key=lambda p: p.timestamp)

        return f"""PRICE DATA ({days} days):
Current: ${latest.close:.2f}
24h Change: {latest.price_change_24h:.2f}% if {latest.price_change_24h} else 'N/A'
Market Cap: ${latest.market_cap:,.0f} if {latest.market_cap} else 'N/A'
Volume: ${latest.volume:,.0f}
High: ${max(p.close for p in prices):.2f}
Low: ${min(p.close for p in prices):.2f}
Range: {price_list[0].timestamp.date()} to {latest.timestamp.date()}"""

    def get_transaction_data(self, days: int = 30) -> str:
        cutoff = datetime.now() - timedelta(days=days)
        txns = self.db.query(TransactionData).filter(
            TransactionData.day >= cutoff
        ).order_by(TransactionData.day.desc()).all()

        if not txns:
            return "No transaction data available"

        latest = txns[0]
        avg_txns = sum(t.transaction_count for t in txns) / len(txns)
        avg_addrs = sum(t.unique_addresses for t in txns) / len(txns)

        return f"""ON-CHAIN METRICS ({days} days):
Latest Transactions: {latest.transaction_count:,.0f}
Avg Daily Transactions: {avg_txns:,.0f}
Latest Addresses: {latest.unique_addresses:,.0f}
Avg Addresses: {avg_addrs:,.0f}
Latest Gas: {latest.gas_used:,.0f}
Data Points: {len(txns)} days"""

    def get_news_data(self, days: int = 30) -> str:
        cutoff = datetime.now() - timedelta(days=days)
        news = self.db.query(NewsData).filter(
            NewsData.published_at >= cutoff
        ).order_by(NewsData.published_at.desc()).all()

        if not news:
            return "No news data available"

        total = len(news)
        pos = sum(1 for n in news if n.sentiment == 'positive')
        neg = sum(1 for n in news if n.sentiment == 'negative')
        neu = total - pos - neg

        headlines = "\n".join([
            f"{i}. [{n.sentiment.upper()}] {n.title[:80]}"
            for i, n in enumerate(news[:5], 1)
        ])

        return f"""NEWS SENTIMENT ({days} days):
Total: {total} articles
Positive: {pos} ({pos/total*100:.1f}%)
Negative: {neg} ({neg/total*100:.1f}%)
Neutral: {neu} ({neu/total*100:.1f}%)

Headlines:
{headlines}"""

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()




if __name__ == "__main__":
    dq = DataQuery()
    print(f"\n ---- Price data from db: \n {dq.get_price_data()}")