"""
Test Alert System
Kiểm tra toàn bộ hệ thống alert
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.alerts.alert_detector import AlertDetector
from src.alerts.discord_sender import DiscordAlertSender

def test_alert_detection():
    """Test alert detection với dữ liệu giả"""

    print("="*60)
    print("TEST ALERT DETECTION SYSTEM")
    print("="*60)

    # Tạo dữ liệu test
    test_data = pd.DataFrame({
        'ticker': ['VCB'] * 5,
        'close': [56.0, 56.5, 57.0, 56.7, 56.5],
        'rsi': [65.0, 68.0, 72.0, 75.0, 28.0],  # RSI cuối = 28 (oversold)
        'ma5': [56.0, 56.2, 56.5, 56.7, 56.6],
        'ma20': [57.0, 57.0, 57.0, 57.5, 57.4],
        'volume': [1000000, 1100000, 1200000, 1150000, 1180000],
        'macd_main': [-0.5, -0.3, -0.1, 0.1, 0.3],
        'macd_signal': [0.2, 0.1, 0.0, -0.1, -0.2],
    })

    # Test 1: Alert Detector
    print("\n1. Testing Alert Detector...")
    detector = AlertDetector()
    alerts = detector.detect_all_alerts(test_data)

    print(f"   Found {len(alerts)} alerts:")
    for i, alert in enumerate(alerts, 1):
        print(f"   {i}. {alert['type']} - {alert['severity']}: {alert['message']}")

    # Test 2: Discord Sender (nếu có alerts)
    if alerts:
        print("\n2. Testing Discord Sender...")
        sender = DiscordAlertSender()

        # Gửi alert đầu tiên
        test_alert = alerts[0]
        print(f"   Sending alert: {test_alert['message']}")

        success = sender.send_alert(test_alert)
        if success:
            print("   ✅ Alert sent to Discord successfully!")
        else:
            print("   ❌ Failed to send alert to Discord")

    # Test 3: Kiểm tra database
    print("\n3. Checking database...")
    import psycopg2
    from src.config import Config

    conn = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )
    cur = conn.cursor()

    # Đếm alerts trong 24h gần nhất
    cur.execute("""
        SELECT COUNT(*)
        FROM stock.technical_alerts
        WHERE created_at > NOW() - INTERVAL '24 hours'
    """)
    count_24h = cur.fetchone()[0]
    print(f"   Alerts in last 24h: {count_24h}")

    # Latest alerts
    cur.execute("""
        SELECT ticker, alert_type, alert_level, created_at
        FROM stock.technical_alerts
        ORDER BY created_at DESC
        LIMIT 3
    """)
    latest = cur.fetchall()
    print(f"   Latest 3 alerts:")
    for row in latest:
        print(f"   - {row[0]}: {row[1]} ({row[2]}) at {row[3]}")

    conn.close()

    print("\n" + "="*60)
    print("TEST COMPLETED!")
    print("="*60)

if __name__ == "__main__":
    test_alert_detection()
