# -*- coding: utf-8 -*-
import psycopg2
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config


def insert_sample_alerts():
    conn = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )

    cur = conn.cursor()

    sample_alerts = [
        ('VNM', 'rsi_overbought', 'warning', 'RSI qua mua (75.2) - Co phieu co the dieu chinh giam', 75.2, 85000),
        ('HPG', 'rsi_oversold', 'critical', 'RSI qua ban (18.5) - Co phieu co the phuc hoi tang', 18.5, 24500),
        ('FPT', 'golden_cross', 'info', 'Golden Cross - MA5 cat len MA20, tin hieu tang gia', 102.5, 102500),
        ('VCB', 'volume_spike', 'info', 'Khoi luong tang dot bien (+250%) - Quan tam dac biet', 15000000, 95000),
        ('TCB', 'macd_bullish', 'info', 'MACD Bullish - MACD cat len Signal, tin hieu tang', 1.5, 52000),
        ('VIC', 'death_cross', 'warning', 'Death Cross - MA5 cat xuong MA20, tin hieu giam gia', 38.2, 38200),
        ('MWG', 'bb_breakout', 'warning', 'Gia thung Bollinger Lower Band - Can quan sat', 48500, 48500),
    ]

    print(f"Inserting {len(sample_alerts)} sample alerts...")

    inserted_count = 0
    for ticker, alert_type, alert_level, message, indicator_value, price_at_alert in sample_alerts:
        try:
            cur.execute(
                """
                INSERT INTO stock.technical_alerts
                (ticker, alert_type, alert_level, message, indicator_value, price_at_alert)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (ticker, alert_type, alert_level, message, indicator_value, price_at_alert)
            )
            conn.commit()
            print(f"  - Inserted: {ticker} - {alert_type}")
            inserted_count += 1
        except Exception as e:
            conn.rollback()
            print(f"  - Error inserting {ticker}: {e}")

    print(f"Inserted {inserted_count}/{len(sample_alerts)} alerts successfully!")
    cur.close()
    conn.close()

    print("Sample alerts inserted successfully!")


if __name__ == "__main__":
    insert_sample_alerts()
