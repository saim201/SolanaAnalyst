
# Fetches from CoinDesk, CoinTelegraph, Decrypt, and Solana Status
import feedparser
import requests
import sys
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict
from email.utils import parsedate_to_datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class RSSNewsFetcher:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    RSS_SOURCES = {
        'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'cointelegraph': 'https://cointelegraph.com/rss',
        'decrypt': 'https://decrypt.co/feed',
    }

    STATUS_API_URL = 'https://status.solana.com/api/v2/incidents.json'

    TIMEOUT = 10 

    SOLANA_KEYWORDS = [
        'solana', 'sol', 'layer 1', 'l1',
        'firedancer', 'phantom wallet', 'jupiter', 'jito', 'marinade',
        'raydium', 'orca', 'magic eden', 'metaplex', 'anchor'
    ]

    CRITICAL_KEYWORDS = ['solana outage', 'solana down', 'solana halted', 'network outage', 'network down', 'mainnet stopped', 'mainnet outage']

    HIGH_KEYWORDS = ['upgrade', 'partnership', 'sec', 'regulation', 'lawsuit', 'exploit', 'hack', 'vulnerability', 'etf']

    def __init__(self):
        pass

    def _normalize_title(self, title: str) -> str:
        normalized = title.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)  
        normalized = ' '.join(normalized.split())
        return normalized


    def _is_solana_relevant(self, text: str) -> bool:
        text_lower = text.lower()
        if re.search(r'\bsol\b', text_lower):
            return True

        for keyword in self.SOLANA_KEYWORDS:
            if keyword != 'sol' and keyword in text_lower:
                return True

        return False


    def _calculate_priority(self, article: Dict) -> str:
        title_lower = article['title'].lower()
        content_lower = article['content'].lower()
        combined = title_lower + ' ' + content_lower
        source = article['source']

        if source == 'Solana Status':
            return 'CRITICAL'
        if any(keyword in combined for keyword in self.CRITICAL_KEYWORDS):
            return 'CRITICAL'
        if any(keyword in combined for keyword in self.HIGH_KEYWORDS):
            return 'HIGH'

        return 'MEDIUM'


    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        seen_titles = set()
        unique_articles = []
        for article in articles:
            normalized = self._normalize_title(article['title'])
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique_articles.append(article)

        if len(unique_articles) < len(articles):
            print(f" Deduplicated: removed {len(articles) - len(unique_articles)} duplicates")

        return unique_articles


    def _fetch_rss_feed(self, url: str, source_name: str) -> List[Dict]:
        try:
            feed = feedparser.parse(url, agent=self.USER_AGENT)
            if not feed.entries:
                print(f"  No entries found in {source_name}")
                return []

            articles = []
            for entry in feed.entries:
                try:
                    pub_date = self._parse_pub_date(entry)
                    content = self._extract_content(entry)
                    article = {
                        'title': entry.get('title', 'Untitled'),
                        'url': entry.get('link', ''),
                        'source': source_name,
                        'published_at': pub_date.isoformat() if pub_date else datetime.now().isoformat(),
                        'content': content,
                    }
                    articles.append(article)

                except Exception as e:
                    print(f"  Error parsing entry from {source_name}: {str(e)}")
                    continue

            return articles

        except Exception as e:
            print(f" Error fetching {source_name}: {str(e)}")
            return []

    def _parse_pub_date(self, entry) -> datetime:
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
            if hasattr(entry, 'published'):
                return parsedate_to_datetime(entry.published)
            if hasattr(entry, 'updated'):
                return parsedate_to_datetime(entry.updated)
            return datetime.now()

        except Exception:
            return datetime.now()


    def _extract_content(self, entry) -> str:
        content = ""
        if hasattr(entry, 'summary'):
            content = entry.summary
        elif hasattr(entry, 'description'):
            content = entry.description
        elif hasattr(entry, 'title'):
            content = entry.title

        content = content.replace('<p>', '').replace('</p>', '')
        content = content.replace('<br>', ' ').replace('<br/>', ' ')
        content = content.replace('&nbsp;', ' ')

        return content[:500] if content else ""




    def fetch_coindesk(self) -> List[Dict]:
        articles = self._fetch_rss_feed(
            self.RSS_SOURCES['coindesk'],
            'CoinDesk'
        )

        filtered_articles = []

        for article in articles:
            if self._is_solana_relevant(article['title'] + ' ' + article['content']):
                filtered_articles.append(article)

        if len(filtered_articles) <= len(articles):
            print(f"✅ Featched {len(filtered_articles)}/{len(articles)} CoinDesk articles ")

        return filtered_articles
    



    def fetch_cointelegraph(self) -> List[Dict]:
        articles = self._fetch_rss_feed(
            self.RSS_SOURCES['cointelegraph'],
            'CoinTelegraph'
        )

        filtered_articles = []

        for article in articles:
            if self._is_solana_relevant(article['title'] + ' ' + article['content']):
                filtered_articles.append(article)

        if len(filtered_articles) < len(articles):
            print(f"✅ Fetched {len(filtered_articles)}/{len(articles)} CoinTelegraph articles")

        return filtered_articles
    



    def fetch_decrypt(self) -> List[Dict]:
        articles = self._fetch_rss_feed(
            self.RSS_SOURCES['decrypt'],
            'Decrypt'
        )

        filtered_articles = []

        for article in articles:
            if 'decrypt.co/videos' in article['url']:
                continue

            if self._is_solana_relevant(article['title'] + ' ' + article['content']):
                filtered_articles.append(article)

        print(f"✅ Fetched {len(filtered_articles)}/{len(articles)} Decrypt articles")
        return filtered_articles



    def fetch_solana_status(self) -> List[Dict]:
        try:
            headers = {'User-Agent': self.USER_AGENT}
            response = requests.get(
                self.STATUS_API_URL,
                headers=headers,
                timeout=self.TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            incidents = []

            if 'incidents' not in data:
                print("⚠️  No incidents data in Solana Status API")
                return []

            cutoff_date = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=7)
            # Normalize cutoff_date to naive UTC
            cutoff_date = datetime.fromisoformat(cutoff_date.isoformat().replace('Z', '+00:00')).replace(tzinfo=None)

            for incident in data['incidents']:
                try:
                    created_at = incident.get('created_at', '')
                    updated_at = incident.get('updated_at', '')

                    if created_at:
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if created_dt.tzinfo is not None:
                            created_dt = created_dt.replace(tzinfo=None)
                    else:
                        created_dt = datetime.now()

                    if created_dt < cutoff_date:
                        continue

                    components = incident.get('components', [])
                    affected_services = ', '.join([c.get('name', '') for c in components]) if components else 'Network-wide'

                    content = incident.get('status', 'Unknown')
                    impact = incident.get('impact', 'unknown')

                    article = {
                        'title': f"[{impact.upper()}] {incident.get('name', 'Network Status')}",
                        'url': f"https://status.solana.com/incidents/{incident.get('id', '')}",
                        'source': 'Solana Status',
                        'published_at': created_dt.isoformat(),
                        'content': f"Status: {content} | Affected: {affected_services} | Updated: {updated_at[:10]}",
                    }
                    incidents.append(article)

                except Exception as e:
                    print(f"⚠️  Error parsing incident: {str(e)}")
                    continue

            print(f"✅ Fetched {len(incidents)} incidents from Solana Status")
            return incidents

        except requests.exceptions.Timeout:
            print("❌ Solana Status API request timed out")
            return []
        except requests.exceptions.ConnectionError:
            print("❌ Failed to connect to Solana Status API")
            return []
        except Exception as e:
            print(f"❌ Error fetching Solana Status: {str(e)}")
            return []

    def fetch_all_sources(self, days_back: int = 7) -> List[Dict]:
        print(f"\nFetching Solana news (last {days_back} days)...\n")

        all_articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        all_articles.extend(self.fetch_coindesk())
        all_articles.extend(self.fetch_cointelegraph())
        all_articles.extend(self.fetch_decrypt())
        all_articles.extend(self.fetch_solana_status())

        filtered_articles = []
        for article in all_articles:
            try:
                pub_date = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                if pub_date >= cutoff_date:
                    filtered_articles.append(article)
            except Exception:
                filtered_articles.append(article)

        deduplicated = self._deduplicate_articles(filtered_articles)

        for article in deduplicated:
            article['priority'] = self._calculate_priority(article)
            try:
                pub_dt = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                # Strip timezone info for consistent comparison
                if pub_dt.tzinfo is not None:
                    pub_dt = pub_dt.replace(tzinfo=None)
                article['_sort_date'] = pub_dt
            except Exception:
                article['_sort_date'] = datetime.min

        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2}
        deduplicated.sort(key=lambda x: (
            priority_order.get(x['priority'], 2),
            -x['_sort_date'].timestamp()
        ))

        for article in deduplicated:
            article.pop('_sort_date', None)

        print(f"\n✅ Total: {len(deduplicated)} articles from all sources")

        priority_counts = {}
        for article in deduplicated:
            priority = article['priority']
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        for priority in ['CRITICAL', 'HIGH', 'MEDIUM']:
            count = priority_counts.get(priority, 0)
            if count > 0:
                print(f"   {priority:8} {count:3} articles")
        print()

        return deduplicated

    def fetch_and_save_to_db(self, days: int = 7) -> bool:
        try:
            from database.data_manager import DataManager

            articles = self.fetch_all_sources(days_back=days)

            if articles:
                with DataManager() as manager:
                    manager.save_news_data(articles)
                print(f" Saved {len(articles)} articles to database")
                return True
            else:
                print("❌ No articles fetched")
                return False

        except Exception as e:
            print(f"❌ Error saving to database: {str(e)}")
            return False


def main():
    print("=" * 80)
    print("Testing Multi-Source RSS News Fetcher for Solana")
    print("=" * 80)

    fetcher = RSSNewsFetcher()


    fetcher.fetch_and_save_to_db()


if __name__ == "__main__":
    main()
