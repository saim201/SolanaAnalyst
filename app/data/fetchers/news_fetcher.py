import sys
import os
import re
import json


backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.agents.llm import llm





NEWS_LOOKBACK_DAYS = 5 

TWITTER_LOOKBACK_HOURS = 48  
REDDIT_LOOKBACK_HOURS = 72   

ONCHAIN_24H = 1    
ONCHAIN_7D = 7     
ONCHAIN_30D = 30   




SYSTEM_PROMPT = """You are a data extraction specialist for Solana (SOL) cryptocurrency. Your job is simple: use web_search to find current data, extract exact values, apply basic classification rules, and return structured JSON.

What you do:
- Search the web for real-time Solana metrics
- Extract exact numbers, headlines, and timestamps
- Classify sentiment using simple rules (positive/negative/neutral)
- Classify trends using percentage thresholds
- Return complete JSON structure

What you DON'T do:
- Don't provide trading advice
- Don't interpret what the data means for prices
- Don't skip searches - keep trying until you find data
- Don't make up numbers - if unavailable, mark as null

You are gathering raw fundamental data for a trading system."""


FETCHER_PROMPT = f"""
TASK: Search the web and fetch Solana fundamental data. Return structured JSON.

Current Time: {{current_datetime_utc}}


═══════════════════════════════════════════════════════════════════════════
1. ON-CHAIN METRICS
═══════════════════════════════════════════════════════════════════════════

Search these NOW:
- "Solana network statistics today"
- "site:theblock.co Solana on-chain data"
- "Solana daily active addresses transactions"

Extract and calculate:
- Daily active addresses: current, 24h ago, 7d ago, 30d ago → calculate % changes
- Daily transactions: current, 24h ago, 7d ago, 30d ago → calculate % changes  
- New wallets (24h): current, 24h ago, 7d ago, 30d ago → calculate % changes
- Transaction success rate: current %

Classify trend using 7d change:
- >+10% = "strong_growth"
- +3% to +10% = "moderate_growth"
- -3% to +3% = "stable"
- -10% to -3% = "moderate_decline"
- <-10% = "strong_decline"


═══════════════════════════════════════════════════════════════════════════
2. NEWS - CRYPTO.NEWS
═══════════════════════════════════════════════════════════════════════════

Search: "site:crypto.news Solana" (last {NEWS_LOOKBACK_DAYS} days)

For each article extract:
- title (exact headline)
- url (full link)
- published_date (YYYY-MM-DD)
- snippet (first 1-2 sentences if available)

Classify sentiment:
- POSITIVE: partnerships, upgrades, adoption, bullish news
- NEGATIVE: hacks, exploits, lawsuits, network issues
- NEUTRAL: factual reporting, no clear bias
- MIXED: both positive and negative elements

Add brief reason (1 sentence) for sentiment classification.


═══════════════════════════════════════════════════════════════════════════
3. NEWS - COINDESK
═══════════════════════════════════════════════════════════════════════════

Search: "site:coindesk.com Solana" (last {NEWS_LOOKBACK_DAYS} days)

Same as above:
- Extract title, url, date, snippet
- Check if sentiment is pre-tagged by CoinDesk
- If not tagged, classify using same rules
- Note if sentiment was "coindesk_tagged" or "llm_classified"


═══════════════════════════════════════════════════════════════════════════
4. TWITTER SENTIMENT
═══════════════════════════════════════════════════════════════════════════

Search:
- "Solana Twitter last {TWITTER_LOOKBACK_HOURS} hours"
- "#Solana trending tweets"

Find 10-15 high engagement tweets.

For each tweet extract:
- tweet_text (content or summary)
- author (username if visible)
- author_type (influencer/developer/community/official/unknown)
- timestamp_relative ("X hours ago")
- engagement (high/medium/low)
- sentiment (positive/negative/neutral/unknown)
- sentiment_reasoning (1 sentence)
- main_topic (price_speculation/ecosystem_update/technical_analysis/fud/hype/other)

After all tweets:
- Count positive/negative/neutral
- Calculate percentages
- List top 3 trending topics


═══════════════════════════════════════════════════════════════════════════
5. REDDIT SENTIMENT
═══════════════════════════════════════════════════════════════════════════

Search:
- "site:reddit.com/r/solana" (last {REDDIT_LOOKBACK_HOURS} hours)
- "site:reddit.com/r/cryptocurrency Solana" (last {REDDIT_LOOKBACK_HOURS} hours)

Find 8-12 high engagement posts.

For each post extract:
- title
- subreddit (r/solana or r/cryptocurrency)
- upvotes (if visible)
- timestamp_relative ("X hours ago")
- summary (1 sentence)
- sentiment (positive/negative/neutral/unknown)
- sentiment_reasoning (1 sentence)
- main_topic (technical_question/price_discussion/news_sharing/concern/excitement/other)

After all posts:
- Count positive/negative/neutral
- Calculate percentages
- List top 3 discussion topics
- Note any major concerns


═══════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════
YOUR RESPONSE MUST USE THIS EXACT FORMAT:

Provide your trading recommendation in this EXACT JSON format:

<answer>
{{
  "fetch_metadata": {{
    "fetch_timestamp_utc": "YYYY-MM-DD HH:MM:SS",
    "sources_used": {{
      "onchain": "source name",
      "news": "crypto.news, coindesk.com",
      "social": "Twitter, Reddit"
    }},
    "issues_encountered": ["list any problems or missing data"]
  }},

  "onchain_data": {{
    "source_url": "https://...",
    "daily_active_addresses": {{
      "current": 0,
      "24h_ago": 0,
      "7d_ago": 0,
      "30d_ago": 0,
      "change_24h_percent": 0.0,
      "change_7d_percent": 0.0,
      "change_30d_percent": 0.0,
      "trend": "strong_growth|moderate_growth|stable|moderate_decline|strong_decline"
    }},
    "daily_transaction_count": {{
      "current": 0,
      "24h_ago": 0,
      "7d_ago": 0,
      "30d_ago": 0,
      "change_24h_percent": 0.0,
      "change_7d_percent": 0.0,
      "change_30d_percent": 0.0,
      "trend": "..."
    }},
    "new_wallets_24h": {{
      "current": 0,
      "24h_ago": 0,
      "7d_ago": 0,
      "30d_ago": 0,
      "change_24h_percent": 0.0,
      "change_7d_percent": 0.0,
      "change_30d_percent": 0.0,
      "trend": "..."
    }},
    "transaction_success_rate": {{
      "current_percent": 0.0,
      "status": "healthy|degraded|unknown"
    }}
  }},

  "news_data": {{
    "crypto_news_articles": [
      {{
        "title": "...",
        "url": "...",
        "published_date": "YYYY-MM-DD",
        "snippet": "...",
        "sentiment": "positive|negative|neutral|mixed",
        "sentiment_reasoning": "...",
        "key_topic": "partnership|upgrade|price|regulatory|ecosystem|other"
      }}
    ],
    "coindesk_articles": [
      {{
        "title": "...",
        "url": "...",
        "published_date": "YYYY-MM-DD",
        "snippet": "...",
        "sentiment": "...",
        "sentiment_source": "coindesk_tagged|llm_classified",
        "sentiment_reasoning": "...",
        "key_topic": "..."
      }}
    ],
    "aggregate": {{
      "total_articles": 0,
      "positive_count": 0,
      "negative_count": 0,
      "neutral_count": 0,
      "positive_percent": 0.0,
      "negative_percent": 0.0,
      "dominant_sentiment": "positive|negative|neutral|mixed"
    }}
  }},

  "twitter_data": {{
    "tweets": [
      {{
        "tweet_text": "...",
        "author": "...",
        "author_type": "...",
        "timestamp_relative": "...",
        "engagement": "high|medium|low",
        "sentiment": "...",
        "sentiment_reasoning": "...",
        "main_topic": "..."
      }}
    ],
    "aggregate": {{
      "total_tweets": 0,
      "positive_count": 0,
      "negative_count": 0,
      "neutral_count": 0,
      "positive_percent": 0.0,
      "negative_percent": 0.0,
      "top_topics": ["topic1", "topic2", "topic3"]
    }}
  }},

  "reddit_data": {{
    "posts": [
      {{
        "title": "...",
        "subreddit": "...",
        "upvotes": 0,
        "timestamp_relative": "...",
        "summary": "...",
        "sentiment": "...",
        "sentiment_reasoning": "...",
        "main_topic": "..."
      }}
    ],
    "aggregate": {{
      "total_posts": 0,
      "positive_count": 0,
      "negative_count": 0,
      "positive_percent": 0.0,
      "negative_percent": 0.0,
      "top_topics": ["topic1", "topic2", "topic3"],
      "key_concerns": ["concern1", "concern2"]
    }}
  }}
}}
</answer>

CRITICAL:
- Use web_search tool to find REAL data
- If data unavailable after searching: set to null, note in issues_encountered
- Follow classification rules exactly
- Complete JSON structure required (even if some fields are null)
- Keep thinking section brief (150-300 words)

START SEARCHING NOW.
"""




def generate_fetcher_prompt():
    from datetime import datetime, UTC

    current_datetime = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    full_prompt = f"{SYSTEM_PROMPT}\n\n{FETCHER_PROMPT}"
    full_prompt = full_prompt.replace("{current_datetime_utc}", current_datetime)

    return full_prompt


def fetch_news_data(model: str = "claude-3-5-haiku-20241022", temperature: float = 0.3):


    full_prompt = generate_fetcher_prompt()

    response = llm(
        full_prompt,
        model=model,
        temperature=temperature,
        max_tokens=4000 
    )

    try:
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
        thinking = thinking_match.group(1).strip() if thinking_match else ""

        answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
        if answer_match:
            answer_json = answer_match.group(1).strip()
        else:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                answer_json = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")

        answer_json = answer_json.strip()
        answer_json = re.sub(r'^```json\s*', '', answer_json)
        answer_json = re.sub(r'\s*```$', '', answer_json)
        first_brace = answer_json.find('{')
        last_brace = answer_json.rfind('}')
        if first_brace != -1 and last_brace != -1:
            answer_json = answer_json[first_brace:last_brace+1]

        answer_json = answer_json.replace('"', '"').replace('"', '"')
        answer_json = answer_json.replace(''', "'").replace(''', "'")

        news_data = json.loads(answer_json)
        news_data['_thinking'] = thinking

        return news_data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Attempted to parse: {answer_json[:500]}...")
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        print(f"Error extracting data from LLM response: {e}")
        print(f"Raw response (first 500 chars): {response[:500]}...")
        raise



if __name__ == "__main__":
    print("=" * 80)
    print("SOLANA FUNDAMENTAL DATA FETCHER")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  News Lookback: {NEWS_LOOKBACK_DAYS} days")
    print(f"  Twitter Lookback: {TWITTER_LOOKBACK_HOURS} hours")
    print(f"  Reddit Lookback: {REDDIT_LOOKBACK_HOURS} hours")
    print(f"  On-Chain Comparisons: 24h, 7d, 30d")
    print(f"\nPrompt ready for Claude!")
    print("=" * 80)
    
    result = fetch_news_data()
    print(f"\nPrompt length: {len(result)} characters")
    print("\n----- result: \n", result)
