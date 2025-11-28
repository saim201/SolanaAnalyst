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



    def get_price_data_sliced(self) -> str:
        now = datetime.now()
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)
        cutoff_90d = now - timedelta(days=90)

        prices_7d = self.db.query(PriceData).filter(
            PriceData.timestamp >= cutoff_7d
        ).order_by(PriceData.timestamp).all()

        prices_30d = self.db.query(PriceData).filter(
            PriceData.timestamp >= cutoff_30d,
            PriceData.timestamp < cutoff_7d
        ).order_by(PriceData.timestamp).all()

        prices_90d = self.db.query(PriceData).filter(
            PriceData.timestamp >= cutoff_90d,
            PriceData.timestamp < cutoff_30d
        ).order_by(PriceData.timestamp).all()

        result = "PRICE DATA (SLICED):\n\n"

        if prices_7d:
            result += "LAST 7 DAYS (Daily Candles):\n"
            for p in prices_7d:
                result += f"  {p.timestamp.strftime('%Y-%m-%d %H:%M')}: Open: ${p.open:.2f}, Close: ${p.close:.2f}, High: ${p.high:.2f}, Low: ${p.low:.2f}, Vol: ${p.volume:,.0f}\n"
        else:
            result += "LAST 7 DAYS: No data\n"

        if prices_30d:
            avg_open = sum(p.open for p in prices_30d) / len(prices_30d)
            avg_close = sum(p.close for p in prices_30d) / len(prices_30d)
            high_30d = max(p.high for p in prices_30d)
            low_30d = min(p.low for p in prices_30d)
            avg_vol = sum(p.volume for p in prices_30d) / len(prices_30d)
            result += f"\nLAST 30 DAYS (Weekly Aggregate):\n  Avg Open: ${avg_open:.2f}, Avg Close: ${avg_close:.2f}, High: ${high_30d:.2f}, Low: ${low_30d:.2f}, Avg Vol: ${avg_vol:,.0f}\n"
        else:
            result += "\nLAST 30 DAYS: No data\n"

        if prices_90d:
            avg_open = sum(p.open for p in prices_90d) / len(prices_90d)
            avg_close = sum(p.close for p in prices_90d) / len(prices_90d)
            high_90d = max(p.high for p in prices_90d)
            low_90d = min(p.low for p in prices_90d)
            avg_vol = sum(p.volume for p in prices_90d) / len(prices_90d)
            result += f"\nLAST 90 DAYS (Monthly Aggregate):\n  Avg Open: ${avg_open:.2f}, Avg Close: ${avg_close:.2f}, High: ${high_90d:.2f}, Low: ${low_90d:.2f}, Avg Vol: ${avg_vol:,.0f}"
        else:
            result += "\nLAST 90 DAYS: No data"

        return result
    


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



    def get_transaction_data_sliced(self) -> str:
        now = datetime.now()
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)
        cutoff_90d = now - timedelta(days=90)

        txns_7d = self.db.query(TransactionData).filter(
            TransactionData.day >= cutoff_7d
        ).order_by(TransactionData.day).all()

        txns_30d = self.db.query(TransactionData).filter(
            TransactionData.day >= cutoff_30d,
            TransactionData.day < cutoff_7d
        ).order_by(TransactionData.day).all()

        txns_90d = self.db.query(TransactionData).filter(
            TransactionData.day >= cutoff_90d,
            TransactionData.day < cutoff_30d
        ).order_by(TransactionData.day).all()

        result = "ON-CHAIN METRICS (SLICED DATA):\n\n"

        if txns_7d:
            result += "LAST 7 DAYS (Daily):\n"
            for txn in txns_7d:
                result += f"  {txn.day.strftime('%Y-%m-%d')}: {txn.transaction_count:,.0f} txns, {txn.unique_addresses:,.0f} addrs, {txn.gas_used:,.0f} gas\n"
        else:
            result += "LAST 7 DAYS: No data\n"

        if txns_30d:
            avg_txns = sum(t.transaction_count for t in txns_30d) / len(txns_30d)
            avg_addrs = sum(t.unique_addresses for t in txns_30d) / len(txns_30d)
            avg_gas = sum(t.gas_used for t in txns_30d) / len(txns_30d)
            result += f"\nLAST 30 DAYS (Weekly Aggregate):\n  Avg Txns: {avg_txns:,.0f}, Avg Addrs: {avg_addrs:,.0f}, Avg Gas: {avg_gas:,.0f}\n"
        else:
            result += "\nLAST 30 DAYS: No data\n"

        if txns_90d:
            avg_txns = sum(t.transaction_count for t in txns_90d) / len(txns_90d)
            avg_addrs = sum(t.unique_addresses for t in txns_90d) / len(txns_90d)
            avg_gas = sum(t.gas_used for t in txns_90d) / len(txns_90d)
            result += f"\nLAST 90 DAYS (Monthly Aggregate):\n  Avg Txns: {avg_txns:,.0f}, Avg Addrs: {avg_addrs:,.0f}, Avg Gas: {avg_gas:,.0f}"
        else:
            result += "\nLAST 90 DAYS: No data"

        return result

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

    def get_news_data_sliced(self) -> str:
        now = datetime.now()
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)
        cutoff_90d = now - timedelta(days=90)

        news_7d = self.db.query(NewsData).filter(
            NewsData.published_at >= cutoff_7d
        ).order_by(NewsData.published_at.desc()).all()

        news_30d = self.db.query(NewsData).filter(
            NewsData.published_at >= cutoff_30d,
            NewsData.published_at < cutoff_7d
        ).order_by(NewsData.published_at.desc()).all()

        news_90d = self.db.query(NewsData).filter(
            NewsData.published_at >= cutoff_90d,
            NewsData.published_at < cutoff_30d
        ).order_by(NewsData.published_at.desc()).all()

        result = "NEWS SENTIMENT (SLICED DATA):\n\n"

        if news_7d:
            result += "LAST 7 DAYS (Headlines + Sentiment):\n"
            pos_7d = sum(1 for n in news_7d if n.sentiment == 'positive')
            neg_7d = sum(1 for n in news_7d if n.sentiment == 'negative')
            neu_7d = len(news_7d) - pos_7d - neg_7d
            result += f"  Sentiment: Positive: {pos_7d}, Negative: {neg_7d}, Neutral: {neu_7d}\n"

            top_headlines = "\n".join([
                f"  {i}. [{n.sentiment.upper()}] {n.title[:75]}"
                for i, n in enumerate(news_7d[:5], 1)
            ])
            result += f"  Top Headlines:\n{top_headlines}\n"
        else:
            result += "LAST 7 DAYS: No news\n"

        if news_30d:
            pos_30d = sum(1 for n in news_30d if n.sentiment == 'positive')
            neg_30d = sum(1 for n in news_30d if n.sentiment == 'negative')
            neu_30d = len(news_30d) - pos_30d - neg_30d
            total_30d = len(news_30d)
            result += f"\n DAYS 7-30 (Sentiment Trend):\n"
            result += f"  Total Articles: {total_30d}, Positive: {pos_30d} ({pos_30d/total_30d*100:.0f}%), Negative: {neg_30d} ({neg_30d/total_30d*100:.0f}%), Neutral: {neu_30d} ({neu_30d/total_30d*100:.0f}%)\n"
        else:
            result += "\n DAYS 7-30: No news\n"

        # Days 30-90: Show long-term sentiment
        if news_90d:
            pos_90d = sum(1 for n in news_90d if n.sentiment == 'positive')
            neg_90d = sum(1 for n in news_90d if n.sentiment == 'negative')
            neu_90d = len(news_90d) - pos_90d - neg_90d
            total_90d = len(news_90d)
            result += f"\nDAYS 30-90 (Long-term Sentiment):\n"
            result += f"  Total Articles: {total_90d}, Positive: {pos_90d} ({pos_90d/total_90d*100:.0f}%), Negative: {neg_90d} ({neg_90d/total_90d*100:.0f}%), Neutral: {neu_90d} ({neu_90d/total_90d*100:.0f}%)"
        else:
            result += "\nDAYS 30-90: No news"

        return result

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()




if __name__ == "__main__":
    dq = DataQuery()
    print(f"\n ---- price slice data from db: \n {dq.get_news_data_sliced()}")