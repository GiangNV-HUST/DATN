"""
Kafka Stock Importer - Import stock data through Kafka pipeline
Sends stock data to Kafka topic for processing by Enhanced Consumer

Flow: VnStock API -> Kafka Producer -> Kafka Topic -> Consumer -> Database
"""

import sys
import os
import io

# Fix encoding for Windows terminal (vnstock uses emojis)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import time
import logging
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnstock import Vnstock
from src.kafka_producer.producer import StockDataProducer
from src.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Top stocks to import (by sector)
TOP_STOCKS = {
    "banks": ["VCB", "TCB", "CTG", "MBB", "VPB", "BID", "ACB", "STB", "HDB", "TPB"],
    "technology": ["FPT", "CMG", "ELC"],
    "real_estate": ["VIC", "VHM", "VRE", "NVL", "KDH", "DXG"],
    "steel": ["HPG", "HSG", "NKG", "SMC"],
    "consumer": ["VNM", "MSN", "SAB"],
    "retail": ["MWG", "PNJ"],
    "oil_gas": ["GAS", "PLX", "PVD", "PVS"],
    "power": ["POW"],
    "securities": ["SSI", "VCI", "HCM", "VND", "SHS"],
    "others": ["REE", "DGC", "GVR", "DHG", "DPM"]
}

# Rate limiting for VCI API
_last_api_call = 0
_API_DELAY = 3  # seconds between API calls


def rate_limit():
    """Apply rate limiting for API calls"""
    global _last_api_call
    elapsed = time.time() - _last_api_call
    if elapsed < _API_DELAY:
        sleep_time = _API_DELAY - elapsed
        logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
        time.sleep(sleep_time)
    _last_api_call = time.time()


def fetch_stock_data(ticker: str, days: int = 60) -> dict:
    """
    Fetch stock data from VnStock API

    Returns:
        dict with keys: ticker, price_history, overview, fundamentals
    """
    rate_limit()

    try:
        stock = Vnstock().stock(symbol=ticker, source='VCI')

        # Get price history
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        price_df = stock.quote.history(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval='1D'
        )

        if price_df is None or price_df.empty:
            logger.warning(f"No price data for {ticker}")
            return None

        # Rename columns to match expected format
        price_df = price_df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # Handle time column
        if 'time' not in price_df.columns:
            if 'TradingDate' in price_df.columns:
                price_df['time'] = price_df['TradingDate']
            elif price_df.index.name == 'time' or isinstance(price_df.index, (pd.DatetimeIndex)):
                price_df = price_df.reset_index()
                if 'index' in price_df.columns:
                    price_df = price_df.rename(columns={'index': 'time'})

        # Get company overview (exchange, industry)
        # VnStock returns: icb_name3 for industry classification, exchange for stock exchange
        overview = {}
        try:
            rate_limit()
            overview_data = stock.company.overview()
            if overview_data is not None and not overview_data.empty:
                if isinstance(overview_data, pd.DataFrame):
                    row = overview_data.iloc[0] if len(overview_data) > 0 else {}
                    # icb_name3 is the industry classification in VnStock
                    industry = row.get('icb_name3') or row.get('icb_name2') or row.get('industry')
                    exchange = row.get('exchange') or 'HOSE'  # Default to HOSE
                    overview = {
                        'exchange': exchange,
                        'industry': industry
                    }
                    logger.debug(f"{ticker} overview: exchange={exchange}, industry={industry}")
        except Exception as e:
            logger.warning(f"Could not get overview for {ticker}: {e}")

        # Get fundamentals (PE, PB, ROE)
        # VnStock returns MultiIndex columns: ('Category', 'Metric')
        fundamentals = {}
        try:
            rate_limit()
            ratio_data = stock.finance.ratio(period='quarter', lang='en')
            if ratio_data is not None and not ratio_data.empty:
                # Flatten MultiIndex columns if present
                if isinstance(ratio_data.columns, pd.MultiIndex):
                    # Create a mapping from metric name to value
                    latest = ratio_data.iloc[-1]
                    ratio_dict = {}
                    for col in ratio_data.columns:
                        if isinstance(col, tuple):
                            metric_name = col[1]  # Get the metric name (second level)
                            ratio_dict[metric_name] = latest[col]
                        else:
                            ratio_dict[col] = latest[col]
                else:
                    ratio_dict = ratio_data.iloc[-1].to_dict()

                # Extract values using the actual column names from VnStock
                pe_val = ratio_dict.get('P/E') or ratio_dict.get('PE')
                pb_val = ratio_dict.get('P/B') or ratio_dict.get('PB')
                roe_val = ratio_dict.get('ROE (%)') or ratio_dict.get('ROE')
                eps_val = ratio_dict.get('EPS (VND)') or ratio_dict.get('EPS')
                div_val = ratio_dict.get('Dividend yield (%)') or ratio_dict.get('Dividend Yield')

                # Note: ROE from VnStock is in decimal form (0.1 = 10%), need to multiply by 100
                fundamentals = {
                    'pe': float(pe_val) if pe_val and not pd.isna(pe_val) else None,
                    'pb': float(pb_val) if pb_val and not pd.isna(pb_val) else None,
                    'roe': float(roe_val) * 100 if roe_val and not pd.isna(roe_val) else None,  # Convert to %
                    'eps': float(eps_val) if eps_val and not pd.isna(eps_val) else None,
                    'dividend_yield': float(div_val) if div_val and not pd.isna(div_val) else None
                }
        except Exception as e:
            logger.warning(f"Could not get fundamentals for {ticker}: {e}")

        # Convert timestamps to ISO format strings for JSON serialization
        price_records = price_df.to_dict(orient='records')
        for record in price_records:
            if 'time' in record and hasattr(record['time'], 'isoformat'):
                record['time'] = record['time'].isoformat()

        return {
            'ticker': ticker,
            'price_history': price_records,
            'overview': overview,
            'fundamentals': fundamentals,
            'fetched_at': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return None


def import_via_kafka(stocks: list = None, days: int = 60):
    """
    Import stock data through Kafka pipeline

    Args:
        stocks: List of tickers to import (default: all TOP_STOCKS)
        days: Number of days of history to fetch
    """
    # Flatten stock list
    if stocks is None:
        stocks = []
        for sector_stocks in TOP_STOCKS.values():
            stocks.extend(sector_stocks)

    logger.info(f"Starting Kafka import for {len(stocks)} stocks")
    logger.info(f"Kafka topic: {Config.KAFKA_TOPIC_STOCK_PRICES}")

    # Initialize producer
    try:
        producer = StockDataProducer()
    except Exception as e:
        logger.error(f"Failed to connect to Kafka: {e}")
        logger.error("Make sure Kafka is running (docker-compose up kafka)")
        return

    success_count = 0
    failed_count = 0

    for i, ticker in enumerate(stocks, 1):
        logger.info(f"[{i}/{len(stocks)}] Fetching {ticker}...")

        # Fetch data from VnStock
        data = fetch_stock_data(ticker, days)

        if data is None:
            logger.warning(f"Skipping {ticker} - no data")
            failed_count += 1
            continue

        # Send to Kafka
        success = producer.send_stock_data(ticker, data)

        if success:
            success_count += 1
            logger.info(f"Sent {ticker} to Kafka ({len(data['price_history'])} records)")
        else:
            failed_count += 1
            logger.error(f"Failed to send {ticker} to Kafka")

        # Progress update
        if i % 10 == 0:
            logger.info(f"Progress: {i}/{len(stocks)} ({success_count} success, {failed_count} failed)")

    # Cleanup
    producer.close()

    logger.info("=" * 60)
    logger.info("KAFKA IMPORT COMPLETED")
    logger.info(f"  Total: {len(stocks)}")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed: {failed_count}")
    logger.info("=" * 60)
    logger.info("Data sent to Kafka. Consumer will process and save to database.")


def main():
    """Main entry point"""
    import argparse
    import pandas as pd

    # Make pandas available in fetch_stock_data
    globals()['pd'] = pd

    parser = argparse.ArgumentParser(description='Import stock data via Kafka')
    parser.add_argument('--stocks', nargs='+', help='Specific stocks to import')
    parser.add_argument('--days', type=int, default=60, help='Days of history')
    parser.add_argument('--sector', type=str, help='Import specific sector')

    args = parser.parse_args()

    stocks = args.stocks
    if args.sector and args.sector in TOP_STOCKS:
        stocks = TOP_STOCKS[args.sector]

    import_via_kafka(stocks=stocks, days=args.days)


if __name__ == '__main__':
    main()
