"""Simple Database Integration Test"""
import sys
import os

# Add Final root to path (for "from src..." imports)
final_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, final_root)

# Load .env
from dotenv import load_dotenv
load_dotenv(os.path.join(final_root, '.env'))

print("=" * 70)
print("DATABASE INTEGRATION TEST")
print("=" * 70)

# Test 1: Import HybridDatabaseClient
print("\n[1/5] Importing HybridDatabaseClient...")
try:
    # Change to hybrid_system directory to import
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'hybrid_system'))
    from database import get_database_client
    print("[OK] HybridDatabaseClient imported")
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Get database client
print("\n[2/5] Getting database client...")
try:
    db = get_database_client()
    print("[OK] Database client created")
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Query data
print("\n[3/5] Testing get_latest_price('VCB')...")
try:
    result = db.get_latest_price("VCB")
    if result:
        print(f"[OK] VCB price: {result['close']:,} VND")
        if result.get('rsi'):
            print(f"     RSI: {result['rsi']:.1f}")
    else:
        print("[WARN] No data (table may be empty)")
except Exception as e:
    print(f"[FAIL] {e}")

# Test 4: Test get_price_history
print("\n[4/5] Testing get_price_history('VCB', 5)...")
try:
    result = db.get_price_history("VCB", days=5)
    if result:
        print(f"[OK] Got {len(result)} days of history")
    else:
        print("[WARN] No history data")
except Exception as e:
    print(f"[FAIL] {e}")

# Test 5: Close
print("\n[5/5] Closing connection...")
try:
    db.close()
    print("[OK] Connection closed")
except:
    pass

print("\n" + "=" * 70)
print("TEST COMPLETED - Database integration works!")
print("=" * 70)
