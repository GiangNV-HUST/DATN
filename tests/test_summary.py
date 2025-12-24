"""
Test script để debug summary endpoint
"""

import sys
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.api.services.stock_services import StockService

# Test function
def test_summary():
    service = StockService()

    print("Testing get_stock_summary for VNM...")
    try:
        result = service.get_stock_summary("VNM")
        print("Success!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_summary()
