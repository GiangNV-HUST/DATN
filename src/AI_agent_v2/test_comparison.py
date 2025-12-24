"""
Test script để so sánh V1 vs V2
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.AI_agent.stock_agent import StockAnalysisAgent
from src.AI_agent_v2.stock_agent_v2 import StockAnalysisAgentV2


def test_question(v1_agent, v2_agent, question):
    """Test 1 câu hỏi với cả V1 và V2"""
    print(f"\n{'='*80}")
    print(f"❓ QUESTION: {question}")
    print(f"{'='*80}\n")

    # Test V1
    print("📌 V1 Response:")
    print("-" * 80)
    try:
        start = time.time()
        v1_response = v1_agent.answer_question(question)
        v1_time = time.time() - start
        print(v1_response)
        print(f"\n⏱️  Time: {v1_time:.2f}s")
    except Exception as e:
        print(f"❌ Error: {e}")
        v1_time = 0

    # Test V2
    print("\n📌 V2 Response (Function Calling):")
    print("-" * 80)
    try:
        start = time.time()
        v2_response = v2_agent.answer_question(question)
        v2_time = time.time() - start
        print(v2_response)
        print(f"\n⏱️  Time: {v2_time:.2f}s")
    except Exception as e:
        print(f"❌ Error: {e}")
        v2_time = 0

    # Comparison
    if v1_time > 0 and v2_time > 0:
        print(f"\n📊 Comparison:")
        print(f"   V1 Time: {v1_time:.2f}s")
        print(f"   V2 Time: {v2_time:.2f}s")
        print(f"   Difference: {abs(v2_time - v1_time):.2f}s ({'+' if v2_time > v1_time else '-'}{abs(v2_time/v1_time - 1)*100:.1f}%)")


def main():
    """Main test function"""
    print("\n" + "="*80)
    print("🧪 TESTING V1 vs V2 AGENTS")
    print("="*80)

    # Initialize agents
    print("\n🔧 Initializing agents...")
    v1_agent = StockAnalysisAgent()
    v2_agent = StockAnalysisAgentV2()
    print("✅ Both agents initialized\n")

    # Test questions
    test_questions = [
        # Simple query
        "VCB giá bao nhiêu?",

        # Complex query
        "VCB có nên mua không? Dự đoán thế nào?",

        # Comparison (V2 should excel)
        "So sánh VCB và TCB về RSI",

        # Search query
        "Tìm cổ phiếu RSI dưới 30",
    ]

    for question in test_questions:
        test_question(v1_agent, v2_agent, question)
        print("\n" + "="*80 + "\n")
        time.sleep(2)  # Tránh rate limit

    print("\n✅ Testing completed!")
    print("\n📝 Summary:")
    print("   - V1: Direct API, fast but rigid")
    print("   - V2: Function Calling, flexible but slower")
    print("   - V2 excels at: complex queries, comparisons, natural language")
    print("   - V1 excels at: simple queries, speed, predictability")


if __name__ == "__main__":
    main()
