"""
Verification script for MCP Server 25 Tools
Kiểm tra xem tất cả tools đã được import đúng chưa
"""

import sys
from pathlib import Path

def verify_imports():
    """Verify all tool imports work correctly"""

    print("🔍 Kiểm tra import paths...\n")

    errors = []
    success = []

    # Test 1: Import shared modules
    try:
        from shared.database import execute_sql_in_thread, create_db_connection
        from shared.constants import VN30_STOCKS, ALERT_TYPES
        success.append("✅ Shared modules (database, constants)")
    except Exception as e:
        errors.append(f"❌ Shared modules: {e}")

    # Test 2: Import stock tools
    try:
        from tools.stock_tools import (
            get_stock_data_mcp,
            get_stock_price_prediction_mcp,
            generate_chart_from_data_mcp,
            get_stock_details_from_tcbs_mcp
        )
        success.append("✅ Stock tools (4 tools)")
    except Exception as e:
        errors.append(f"❌ Stock tools: {e}")

    # Test 3: Import alert tools
    try:
        from tools.alert_tools import (
            create_alert_mcp,
            get_user_alerts_mcp,
            delete_alert_mcp
        )
        success.append("✅ Alert tools (3 tools)")
    except Exception as e:
        errors.append(f"❌ Alert tools: {e}")

    # Test 4: Import subscription tools
    try:
        from tools.subscription_tools import (
            create_subscription_mcp,
            get_user_subscriptions_mcp,
            delete_subscription_mcp
        )
        success.append("✅ Subscription tools (3 tools)")
    except Exception as e:
        errors.append(f"❌ Subscription tools: {e}")

    # Test 5: Import Gemini tools
    try:
        from tools.gemini_tools import (
            gemini_summarize_mcp,
            gemini_search_and_summarize_mcp,
            batch_summarize_mcp
        )
        success.append("✅ Gemini AI tools (3 tools)")
    except Exception as e:
        errors.append(f"❌ Gemini tools: {e}")

    # Test 6: Import finance tools
    try:
        from tools.finance_tools import get_financial_data_mcp
        success.append("✅ Finance tools (1 tool)")
    except Exception as e:
        errors.append(f"❌ Finance tools: {e}")

    # Test 7: Import screener tools
    try:
        from tools.screener_tools import (
            screen_stocks_mcp,
            get_screener_columns_mcp
        )
        success.append("✅ Screener tools (2 tools)")
    except Exception as e:
        errors.append(f"❌ Screener tools: {e}")

    # Test 8: Import investment planning tools
    try:
        from tools.investment_planning_tools import (
            gather_investment_profile,
            calculate_portfolio_allocation,
            generate_entry_strategy,
            generate_risk_management_plan,
            generate_monitoring_plan
        )
        success.append("✅ Investment planning tools (5 tools)")
    except Exception as e:
        errors.append(f"❌ Investment planning tools: {e}")

    # Test 9: Import stock discovery tools
    try:
        from tools.stock_discovery_tools import (
            discover_stocks_by_profile,
            search_potential_stocks,
            filter_stocks_by_criteria,
            rank_stocks_by_score
        )
        success.append("✅ Stock discovery tools (4 tools)")
    except Exception as e:
        errors.append(f"❌ Stock discovery tools: {e}")

    # Print results
    print("\n" + "="*60)
    print("THÀNH CÔNG:")
    print("="*60)
    for s in success:
        print(s)

    if errors:
        print("\n" + "="*60)
        print("LỖI:")
        print("="*60)
        for e in errors:
            print(e)
        print("\n❌ Một số imports thất bại. Kiểm tra lại import paths.")
        return False
    else:
        print("\n" + "="*60)
        print("✅ TẤT CẢ 25 TOOLS ĐÃ SẴN SÀNG!")
        print("="*60)
        print("\n📦 Tổng cộng: 25 tools đã được import thành công")
        print("📝 Đọc README_TOOLS.md để biết thêm chi tiết")
        return True


def check_dependencies():
    """Check if required packages are installed"""

    print("\n🔍 Kiểm tra dependencies...\n")

    required = {
        'psycopg2': 'PostgreSQL adapter',
        'pandas': 'Data manipulation',
        'matplotlib': 'Plotting',
        'mplfinance': 'Financial charts',
        'vnstock': 'Vietnam stock data',
        'google.genai': 'Gemini AI',
        'mcp': 'MCP protocol'
    }

    missing = []
    installed = []

    for package, description in required.items():
        try:
            if '.' in package:
                # For google.genai
                __import__(package.split('.')[0])
            else:
                __import__(package)
            installed.append(f"✅ {package} - {description}")
        except ImportError:
            missing.append(f"❌ {package} - {description}")

    print("Đã cài đặt:")
    for pkg in installed:
        print(pkg)

    if missing:
        print("\nChưa cài đặt:")
        for pkg in missing:
            print(pkg)
        print("\n💡 Chạy: pip install psycopg2-binary pandas matplotlib mplfinance vnstock google-generativeai python-dotenv mcp")
    else:
        print("\n✅ Tất cả dependencies đã được cài đặt!")


if __name__ == "__main__":
    print("="*60)
    print("MCP SERVER 25 TOOLS - VERIFICATION SCRIPT")
    print("="*60)

    # Check dependencies first
    check_dependencies()

    print("\n")

    # Verify imports
    success = verify_imports()

    if success:
        print("\n🚀 Bạn có thể chạy MCP server bằng: python server.py")
    else:
        print("\n⚠️  Sửa lỗi import trước khi chạy server")
        sys.exit(1)
