
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ANTHROPIC_API_KEY')

MODELS = {
    'onchain': 'claude-3-5-haiku-20241022',      # Fast model for technical analysis
    'news': 'claude-3-5-haiku-20241022',          # Fast model for news
    'reflection': 'claude-3-5-haiku-20241022',    # Fast model for reflection
    'trader': 'claude-sonnet-4-5-20250929',       # Best model for final decision
}


START_DATE = "2023-10-01"
END_DATE = "2023-10-03"

STARTING_CASH = 500_000        # Cash ready to buy SOL
STARTING_SOL_VALUE = 500_000   # Dollar value of SOL you start with

DATA_DIR = "data/solana"
PRICE_FILE = f"{DATA_DIR}/solana_daily_price.csv"
TXN_FILE = f"{DATA_DIR}/solana_transaction_statistics.csv"
NEWS_DIR = f"{DATA_DIR}/news"
