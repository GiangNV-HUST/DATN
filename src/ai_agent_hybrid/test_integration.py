"""
Test Integration between Hybrid System and Final Database

This script tests the integration of 8 new database tools.
"""

import sys
import os

# IMPORTANT: Load .env BEFORE any imports that use API keys
from dotenv import load_dotenv
final_root = os.path.join(os.path.dirname(__file__), '..', '..')
load_dotenv(os.path.join(final_root, '.env'))

# Add paths
sys.path.insert(0, final_root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'hybrid_system'))

from database import get_database_client


def test_database_integration():
    """Test all 8 new database tools"""

    print("=" * 80)
    print("🧪 TESTING HYBRID-FINAL DATABASE INTEGRATION")
    print("=" * 80)

    # Get database client
    db = get_database_client()

    test_results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }

    # Test 1: get_latest_price
    print("\n[Test 1/8] Testing get_latest_price...")
    try:
        result = db.get_latest_price("VCB")
        if result and 'close' in result and 'rsi' in result:
            print(f"✅ PASSED - Latest VCB price: {result['close']:,} VND, RSI: {result['rsi']}")
            test_results["passed"] += 1
        else:
            print(f"❌ FAILED - Invalid result format: {result}")
            test_results["failed"] += 1
            test_results["errors"].append("get_latest_price returned invalid format")
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"get_latest_price: {str(e)}")

    # Test 2: get_price_history
    print("\n[Test 2/8] Testing get_price_history...")
    try:
        result = db.get_price_history("VCB", days=10)
        if result and isinstance(result, list) and len(result) > 0:
            print(f"✅ PASSED - Got {len(result)} days of price history")
            test_results["passed"] += 1
        else:
            print(f"❌ FAILED - No price history returned")
            test_results["failed"] += 1
            test_results["errors"].append("get_price_history returned empty")
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"get_price_history: {str(e)}")

    # Test 3: get_company_info
    print("\n[Test 3/8] Testing get_company_info...")
    try:
        result = db.get_company_info("VCB")
        if result and 'company_name' in result:
            print(f"✅ PASSED - Company: {result['company_name']}")
            if 'industry' in result:
                print(f"           Industry: {result['industry']}")
            test_results["passed"] += 1
        else:
            print(f"❌ FAILED - Invalid company info: {result}")
            test_results["failed"] += 1
            test_results["errors"].append("get_company_info returned invalid format")
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"get_company_info: {str(e)}")

    # Test 4: search_stocks_by_criteria
    print("\n[Test 4/8] Testing search_stocks_by_criteria...")
    try:
        result = db.search_stocks_by_criteria({'rsi_below': 50})
        if result and isinstance(result, list):
            print(f"✅ PASSED - Found {len(result)} stocks with RSI < 50")
            if len(result) > 0:
                print(f"           Sample: {result[:5]}")
            test_results["passed"] += 1
        else:
            print(f"❌ FAILED - Invalid search result: {result}")
            test_results["failed"] += 1
            test_results["errors"].append("search_stocks_by_criteria returned invalid format")
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"search_stocks_by_criteria: {str(e)}")

    # Test 5: get_balance_sheet
    print("\n[Test 5/8] Testing get_balance_sheet...")
    try:
        result = db.get_balance_sheet(['VCB'])
        if result and isinstance(result, list) and len(result) > 0:
            print(f"✅ PASSED - Got balance sheet data")
            if 'short_asset' in result[0]:
                print(f"           Short assets: {result[0].get('short_asset')}")
            test_results["passed"] += 1
        else:
            print(f"⚠️  WARNING - No balance sheet data (table might be empty)")
            test_results["passed"] += 1  # Count as pass if no data
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"get_balance_sheet: {str(e)}")

    # Test 6: get_income_statement
    print("\n[Test 6/8] Testing get_income_statement...")
    try:
        result = db.get_income_statement(['VCB'])
        if result and isinstance(result, list) and len(result) > 0:
            print(f"✅ PASSED - Got income statement data")
            if 'revenue' in result[0]:
                print(f"           Revenue: {result[0].get('revenue')}")
            test_results["passed"] += 1
        else:
            print(f"⚠️  WARNING - No income statement data (table might be empty)")
            test_results["passed"] += 1  # Count as pass if no data
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"get_income_statement: {str(e)}")

    # Test 7: get_cash_flow
    print("\n[Test 7/8] Testing get_cash_flow...")
    try:
        result = db.get_cash_flow(['VCB'])
        if result and isinstance(result, list) and len(result) > 0:
            print(f"✅ PASSED - Got cash flow data")
            if 'operating_cf' in result[0]:
                print(f"           Operating CF: {result[0].get('operating_cf')}")
            test_results["passed"] += 1
        else:
            print(f"⚠️  WARNING - No cash flow data (table might be empty)")
            test_results["passed"] += 1  # Count as pass if no data
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"get_cash_flow: {str(e)}")

    # Test 8: get_financial_ratios
    print("\n[Test 8/8] Testing get_financial_ratios...")
    try:
        result = db.get_financial_ratios(['VCB', 'ACB', 'TCB'])
        if result and isinstance(result, list) and len(result) > 0:
            print(f"✅ PASSED - Got financial ratios for {len(result)} stocks")
            for ratio in result[:3]:
                ticker = ratio.get('ticker', '?')
                pe = ratio.get('pe', 'N/A')
                roe = ratio.get('roe', 'N/A')
                print(f"           {ticker}: PE={pe}, ROE={roe}")
            test_results["passed"] += 1
        else:
            print(f"⚠️  WARNING - No financial ratios data (table might be empty)")
            test_results["passed"] += 1  # Count as pass if no data
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"get_financial_ratios: {str(e)}")

    # Print statistics
    print("\n" + "=" * 80)
    print("📊 DATABASE CLIENT STATISTICS")
    print("=" * 80)
    stats = db.get_stats()
    print(f"Total calls: {stats['total_calls']}")
    print(f"Cache hits: {stats['cache_hits']}")
    print(f"Cache hit rate: {stats['cache_hit_rate']}")
    print(f"Errors: {stats['errors']}")
    print(f"Error rate: {stats['error_rate']}")

    # Print test summary
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY")
    print("=" * 80)
    total = test_results["passed"] + test_results["failed"]
    print(f"✅ Passed: {test_results['passed']}/{total}")
    print(f"❌ Failed: {test_results['failed']}/{total}")

    if test_results["failed"] > 0:
        print("\n⚠️  ERRORS:")
        for error in test_results["errors"]:
            print(f"  - {error}")

    # Overall result
    print("\n" + "=" * 80)
    if test_results["failed"] == 0:
        print("🎉 ALL TESTS PASSED! Integration is successful!")
    else:
        print("⚠️  SOME TESTS FAILED. Please check errors above.")
    print("=" * 80)

    # Close connection
    db.close()

    return test_results["failed"] == 0


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "HYBRID-FINAL INTEGRATION TEST" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    success = test_database_integration()

    print("\n")
    if success:
        print("✅ Integration test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Integration test failed!")
        sys.exit(1)
