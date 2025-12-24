import logging
from vnstock_client import VnStockClient

# Setup Logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def test_crawl():
    """Test crawl data từ VnStock"""
    client = VnStockClient()

    # Test lấy dữ liệu 1 phút
    print("\n=== Test 1m data ===")
    df_1m = client.get_intraday_data("VNM")
    if df_1m is not None:
        print(df_1m.head())
        print(f"\nColumns: {df_1m.columns.tolist()}")

    # Test lấy dữ liệu ngày
    print("\n=== Test daily data ===")
    df_1d = client.get_daily_data("VNM")
    if df_1d is not None:
        print(df_1d.tail())
        print(f"\nShape: {df_1d.shape}")
        
if __name__ == "__main__":
    test_crawl()