"""
Test Discord Bot Error Handling
Kiểm tra xem bot có xử lý lỗi đúng cách không
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.AI_agent.stock_agent import StockAnalysisAgent

def test_error_handling():
    """Test xem agent có raise exception khi gặp lỗi không"""

    print("="*60)
    print("Testing AI Agent Error Handling")
    print("="*60)

    agent = StockAnalysisAgent()

    # Test 1: answer_question với quota error
    print("\n1. Testing answer_question (should raise exception)...")
    try:
        response = agent.answer_question("VCB có tốt không?")
        print(f"❌ FAILED: Should have raised exception but returned: {response[:100]}")
    except Exception as e:
        print(f"✅ PASSED: Exception raised correctly")
        print(f"   Error message: {str(e)[:100]}")

    # Test 2: analyze_stock với quota error
    print("\n2. Testing analyze_stock (should raise exception)...")
    try:
        response = agent.analyze_stock("VCB")
        print(f"❌ FAILED: Should have raised exception but returned: {response[:100]}")
    except Exception as e:
        print(f"✅ PASSED: Exception raised correctly")
        print(f"   Error message: {str(e)[:100]}")

    print("\n" + "="*60)
    print("Test completed!")
    print("="*60)

if __name__ == "__main__":
    test_error_handling()
