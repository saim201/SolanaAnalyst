"""
CFGI.io Solana Fear & Greed Index Fetcher

API: https://cfgi.io/api/api_request_v2.php
Cost: 4 credits per call (essential fields: cfgi, social, whales, trends)
Free credits: 100 (at signup)

Caching: Only fetch if last fetch was >4 hours ago (handled by data_manager)
"""

import os
import requests
from datetime import datetime, timezone
from typing import Dict, Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)


@dataclass
class CFGIResponse:
    score: float
    classification: str
    social: Optional[float]
    whales: Optional[float]
    trends: Optional[float]
    price: Optional[float]
    timestamp: datetime

    def to_dict(self) -> Dict:
        return {
            "score": self.score,
            "classification": self.classification,
            "social": self.social,
            "whales": self.whales,
            "trends": self.trends,
            "price": self.price,
            "timestamp": self.timestamp.isoformat()
        }


class CFGIFetcher:

    BASE_URL = "https://cfgi.io/api/api_request_v2.php"
    TIMEOUT = 15
    FIELDS = ["cfgi", "social", "whales", "trends"]

    CLASSIFICATIONS = {
        (0, 20): "Extreme Fear",
        (20, 40): "Fear",
        (40, 60): "Neutral",
        (60, 80): "Greed",
        (80, 101): "Extreme Greed"
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CFGI_API_KEY")
        if not self.api_key:
            raise ValueError("CFGI API key required. Set CFGI_API_KEY environment variable.")
        self.session = requests.Session()

    def _classify_score(self, score: float) -> str:
        for (low, high), label in self.CLASSIFICATIONS.items():
            if low <= score < high:
                return label
        return "Neutral"

    def fetch(self) -> Optional[CFGIResponse]:
        params = {
            "api_key": self.api_key,
            "token": "SOL",
            "period": 4,
            "values": 1,
            "fields": ",".join(self.FIELDS)
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=self.TIMEOUT)

            credits_used = response.headers.get("X-Credits-Used", "?")
            credits_remaining = response.headers.get("X-Credits-Remaining", "?")
            print(f"📊 CFGI API: {credits_used} credits used, {credits_remaining} remaining")

            response.raise_for_status()
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                item = data[0]
            elif isinstance(data, dict):
                if "error" in data:
                    print(f"❌ CFGI API Error: {data['error']}")
                    return None
                item = data
            else:
                print("⚠️ CFGI API returned unexpected format")
                return None

            date_str = item.get("date", "")
            try:
                timestamp = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            except ValueError:
                timestamp = datetime.now(timezone.utc)

            score = float(item.get("cfgi", 50))

            return CFGIResponse(
                score=score,
                classification=self._classify_score(score),
                social=item.get("data_social"),
                whales=item.get("data_whales"),
                trends=item.get("data_trends"),
                price=item.get("price"),
                timestamp=timestamp
            )

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            error_messages = {
                401: "Invalid/Expired API key - Please check your CFGI_API_KEY in .env",
                402: "Insufficient credits - Please top up at cfgi.io",
                429: "Rate limit exceeded (max 1 req/sec)"
            }
            error_msg = error_messages.get(status, 'Unknown error')
            print(f"❌ CFGI API Error ({status}): {error_msg}")

            # Try to parse error response
            try:
                error_data = e.response.json()
                if 'error' in error_data:
                    print(f"   API Message: {error_data['error']}")
            except:
                pass

            return None
        except Exception as e:
            print(f"❌ CFGI Fetch Error: {e}")
            return None

    def get_trading_signal(self, score: float) -> Dict:
        if score < 20:
            return {"signal": "STRONG_BUY", "bias": "BULLISH", "interpretation": f"Extreme fear ({score:.0f}) often marks market bottoms"}
        elif score < 40:
            return {"signal": "BUY", "bias": "BULLISH", "interpretation": f"Fear sentiment ({score:.0f}) suggests accumulation zone"}
        elif score < 60:
            return {"signal": "NEUTRAL", "bias": "NEUTRAL", "interpretation": f"Neutral sentiment ({score:.0f}) - no clear bias"}
        elif score < 80:
            return {"signal": "SELL", "bias": "BEARISH", "interpretation": f"Greed sentiment ({score:.0f}) - consider taking profits"}
        else:
            return {"signal": "STRONG_SELL", "bias": "BEARISH", "interpretation": f"Extreme greed ({score:.0f}) often precedes corrections"}

    def fetch_and_save_to_db(self) -> bool:
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from database.data_manager import DataManager

            # Fetch fresh data from API
            cfgi_response = self.fetch()

            if not cfgi_response:
                print("❌ Failed to fetch CFGI data")
                return False

            # Save to database
            with DataManager() as manager:
                manager.save_cfgi_data(cfgi_response)

            print(f"✅ CFGI data saved: {cfgi_response.classification} ({cfgi_response.score:.1f})")
            return True

        except Exception as e:
            print(f"❌ Error saving CFGI data to DB: {str(e)}")
            return False


if __name__ == "__main__":
    cfgi = CFGIFetcher()
    cfgi.fetch_and_save_to_db()