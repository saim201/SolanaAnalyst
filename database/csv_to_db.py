
import os
import sys
import pandas as pd
import json
from glob import glob
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.data_manager import DataManager


def load_price_data_from_csv(data_dir: str = "data/solana"):
    csv_path = f"{data_dir}/solana_daily_price.csv"

    if not os.path.exists(csv_path):
        print(f"⚠️  Price CSV not found: {csv_path}")
        return None

    print(f"📂 Loading price data from {csv_path}")
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"✅ Loaded {len(df)} price records from CSV")
    return df


def load_transaction_data_from_csv(data_dir: str = "data/solana"):
    csv_path = f"{data_dir}/solana_transaction_statistics.csv"

    if not os.path.exists(csv_path):
        print(f"⚠️  Transaction CSV not found: {csv_path}")
        return None

    print(f"📂 Loading transaction data from {csv_path}")
    df = pd.read_csv(csv_path)
    df['day'] = pd.to_datetime(df['day'])

    print(f"✅ Loaded {len(df)} transaction records from CSV")
    return df


def load_news_data_from_json(data_dir: str = "data/solana/news"):
    if not os.path.exists(data_dir):
        print(f"⚠️  News directory not found: {data_dir}")
        return []

    print(f"📂 Loading news data from {data_dir}")

    all_articles = []
    json_files = glob(f"{data_dir}/*.json")

    for json_file in json_files:
        with open(json_file, 'r') as f:
            articles = json.load(f)
            all_articles.extend(articles)

    print(f"✅ Loaded {len(all_articles)} news articles from {len(json_files)} JSON files")
    return all_articles


def sync_csv_to_database():
    print("=" * 80)
    print("🔄 SYNCING CSV DATA TO DATABASE")
    print("=" * 80)

    with DataManager() as db:
        # Load and save price data
        print("\n1️⃣  Processing price data...")
        price_df = load_price_data_from_csv()
        if price_df is not None and not price_df.empty:
            db.save_price_data(price_df)

        # Load and save transaction data
        print("\n2️⃣  Processing transaction data...")
        txn_df = load_transaction_data_from_csv()
        if txn_df is not None and not txn_df.empty:
            db.save_transaction_data(txn_df)

        # Load and save news data
        print("\n3️⃣  Processing news data...")
        articles = load_news_data_from_json()
        if articles:
            db.save_news_data(articles)

    print("\n" + "=" * 80)
    print("✅ CSV TO DATABASE SYNC COMPLETE")
    print("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Load CSV data into PostgreSQL")
    parser.add_argument(
        '--data-dir',
        type=str,
        default='data/solana',
        help='Directory containing CSV files'
    )

    args = parser.parse_args()

    sync_csv_to_database()


if __name__ == "__main__":
    main()
