"""Test Discord Alert Sender"""

import sys
import os
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.alerts.discord_sender import DiscordAlertSender

def test_discord_alert():
    """Test gửi alert đến Discord"""

    sender = DiscordAlertSender()

    # Tạo fake alert
    test_alert = {
        "type": "RSI_OVERBOUGHT",
        "ticker": "VCB",
        "message": "🔴 VCB RSI = 75.5 (Overbought) - TEST MESSAGE",
        "severity": "WARNING",
        "value": 75.5
    }

    print("="*60)
    print("Testing Discord Alert Sender...")
    print(f"Alert: {test_alert}")
    print("="*60)

    # Gửi alert
    success = sender.send_alert(test_alert)

    if success:
        print("✅ Alert sent successfully to Discord!")
    else:
        print("❌ Failed to send alert to Discord")

    return success

if __name__ == "__main__":
    test_discord_alert()
