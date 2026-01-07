"""
Emergency Retraining Script

Triggers emergency retrain when:
1. MAPE increases suddenly (> 2x threshold)
2. High volatility detected (> 2x average)
3. Major market event (manual trigger)

Usage:
    # Auto check and retrain if needed
    python scripts/emergency_retrain.py --auto

    # Force retrain specific stocks
    python scripts/emergency_retrain.py --force --tickers VCB,HPG

    # Check status only
    python scripts/emergency_retrain.py --check
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

from scripts.retrain_scheduler import RetrainingScheduler


class EmergencyRetrainingSystem:
    """
    System for detecting anomalies and triggering emergency retraining

    Monitors:
    - Prediction accuracy (MAPE)
    - Market volatility
    - Direction accuracy
    """

    def __init__(self):
        self.scheduler = RetrainingScheduler()

        # Thresholds
        self.NORMAL_MAPE_3D = 1.2  # Normal MAPE for 3-day
        self.NORMAL_MAPE_48D = 3.5  # Normal MAPE for 48-day
        self.EMERGENCY_MULTIPLIER = 2.0  # Emergency if MAPE > 2x normal
        self.VOLATILITY_MULTIPLIER = 2.0  # Emergency if volatility > 2x avg

    def check_prediction_accuracy(
        self,
        ticker: str,
        horizon: str,
        days_to_check: int = 3
    ) -> Tuple[bool, str, float]:
        """
        Check recent prediction accuracy

        Args:
            ticker: Stock ticker
            horizon: '3day' or '48day'
            days_to_check: Number of recent days to check

        Returns:
            (needs_retrain, reason, mape)
        """
        # TODO: Implement actual prediction tracking
        # This requires storing predictions in database

        # Query recent predictions
        # query = f"""
        #     SELECT
        #         predicted_price,
        #         actual_price,
        #         ABS((predicted_price - actual_price) / actual_price) * 100 as ape
        #     FROM prediction_log
        #     WHERE ticker = '{ticker}'
        #         AND horizon = '{horizon}'
        #         AND prediction_date >= NOW() - INTERVAL '{days_to_check} days'
        #         AND actual_price IS NOT NULL
        # """
        # df = pd.read_sql(query, conn)
        # recent_mape = df['ape'].mean()

        # Simulate for demo
        # In production, replace with actual query
        recent_mape = np.random.uniform(0.8, 3.5)

        # Determine threshold based on horizon
        normal_mape = self.NORMAL_MAPE_3D if horizon == '3day' else self.NORMAL_MAPE_48D
        emergency_threshold = normal_mape * self.EMERGENCY_MULTIPLIER

        if recent_mape > emergency_threshold:
            return True, f"MAPE too high: {recent_mape:.2f}% (threshold: {emergency_threshold:.2f}%)", recent_mape
        else:
            return False, f"MAPE acceptable: {recent_mape:.2f}%", recent_mape

    def check_market_volatility(
        self,
        ticker: str,
        window: int = 10
    ) -> Tuple[bool, str, float]:
        """
        Check if market volatility is abnormally high

        Args:
            ticker: Stock ticker
            window: Days to calculate volatility

        Returns:
            (high_volatility, reason, volatility_ratio)
        """
        # TODO: Fetch actual stock data
        # from database.connection import get_connection
        # conn = get_connection()
        # query = f"""
        #     SELECT time, close
        #     FROM stock_prices
        #     WHERE ticker = '{ticker}'
        #     ORDER BY time DESC
        #     LIMIT 100
        # """
        # df = pd.read_sql(query, conn)

        # Simulate for demo
        # Generate dummy price data with occasional spikes
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        prices = 100 + np.random.randn(100).cumsum()

        # Add volatility spike
        if np.random.random() > 0.7:  # 30% chance of spike
            prices[-5:] += np.random.choice([-10, 10])

        df = pd.DataFrame({'time': dates, 'close': prices})
        df.set_index('time', inplace=True)

        # Calculate returns and volatility
        returns = df['close'].pct_change()

        # Current volatility (last N days)
        current_vol = returns.tail(window).std()

        # Historical average volatility
        avg_vol = returns.std()

        volatility_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

        if volatility_ratio > self.VOLATILITY_MULTIPLIER:
            return True, f"High volatility: {volatility_ratio:.2f}x average", volatility_ratio
        else:
            return False, f"Normal volatility: {volatility_ratio:.2f}x average", volatility_ratio

    def check_direction_accuracy(
        self,
        ticker: str,
        horizon: str,
        days_to_check: int = 5
    ) -> Tuple[bool, str, float]:
        """
        Check if model is predicting correct direction (up/down)

        Args:
            ticker: Stock ticker
            horizon: '3day' or '48day'
            days_to_check: Number of recent days to check

        Returns:
            (poor_direction, reason, accuracy)
        """
        # TODO: Query prediction log
        # query = f"""
        #     SELECT
        #         predicted_price,
        #         actual_price,
        #         CASE
        #             WHEN (predicted_price - LAG(actual_price)) * (actual_price - LAG(actual_price)) > 0
        #             THEN 1 ELSE 0
        #         END as correct_direction
        #     FROM prediction_log
        #     WHERE ticker = '{ticker}'
        #         AND horizon = '{horizon}'
        #         AND prediction_date >= NOW() - INTERVAL '{days_to_check} days'
        # """
        # df = pd.read_sql(query, conn)
        # direction_accuracy = df['correct_direction'].mean()

        # Simulate
        direction_accuracy = np.random.uniform(0.4, 0.8)

        if direction_accuracy < 0.5:
            return True, f"Poor direction accuracy: {direction_accuracy:.1%} (worse than random)", direction_accuracy
        else:
            return False, f"Good direction accuracy: {direction_accuracy:.1%}", direction_accuracy

    def evaluate_ticker(
        self,
        ticker: str,
        horizon: str
    ) -> Dict:
        """
        Comprehensive evaluation of a ticker-horizon pair

        Returns:
            Dictionary with evaluation results
        """
        print(f"\n{'='*80}")
        print(f"🔍 EVALUATING: {ticker} ({horizon})")
        print(f"{'='*80}")

        result = {
            'ticker': ticker,
            'horizon': horizon,
            'timestamp': datetime.now().isoformat(),
            'needs_emergency_retrain': False,
            'reasons': []
        }

        # Check 1: Prediction accuracy
        print("\n📊 Check 1: Prediction Accuracy")
        needs_retrain_acc, reason_acc, mape = self.check_prediction_accuracy(ticker, horizon)
        print(f"   {reason_acc}")

        if needs_retrain_acc:
            result['needs_emergency_retrain'] = True
            result['reasons'].append(f"MAPE: {reason_acc}")

        result['recent_mape'] = mape

        # Check 2: Market volatility
        print("\n📈 Check 2: Market Volatility")
        high_vol, reason_vol, vol_ratio = self.check_market_volatility(ticker)
        print(f"   {reason_vol}")

        if high_vol:
            result['needs_emergency_retrain'] = True
            result['reasons'].append(f"Volatility: {reason_vol}")

        result['volatility_ratio'] = vol_ratio

        # Check 3: Direction accuracy
        print("\n🎯 Check 3: Direction Accuracy")
        poor_dir, reason_dir, dir_acc = self.check_direction_accuracy(ticker, horizon)
        print(f"   {reason_dir}")

        if poor_dir:
            result['needs_emergency_retrain'] = True
            result['reasons'].append(f"Direction: {reason_dir}")

        result['direction_accuracy'] = dir_acc

        # Final decision
        print(f"\n{'='*80}")
        if result['needs_emergency_retrain']:
            print(f"🚨 EMERGENCY RETRAIN NEEDED")
            for reason in result['reasons']:
                print(f"   ⚠️ {reason}")
        else:
            print(f"✅ Model is performing well")
        print(f"{'='*80}\n")

        return result

    def emergency_retrain(
        self,
        tickers: List[str],
        horizons: List[str] = ['3day', '48day']
    ):
        """
        Perform emergency retraining

        Args:
            tickers: List of tickers to retrain
            horizons: List of horizons to retrain
        """
        print("🚨 EMERGENCY RETRAINING MODE")
        print("="*80)

        results = []

        for ticker in tickers:
            for horizon in horizons:
                # Evaluate first
                eval_result = self.evaluate_ticker(ticker, horizon)

                if eval_result['needs_emergency_retrain']:
                    print(f"\n🔄 Emergency retraining: {ticker} ({horizon})")

                    # TODO: Load actual data and retrain
                    # from database.connection import get_connection
                    # data = load_stock_data(ticker)
                    # retrain_result = self.scheduler.retrain_model(ticker, horizon, data)

                    print(f"   ⚠️ Skipping: Need to implement data loading")

                    eval_result['retrain_status'] = 'skipped'
                else:
                    print(f"   ✅ No emergency retrain needed")
                    eval_result['retrain_status'] = 'not_needed'

                results.append(eval_result)

        # Summary
        print("\n" + "="*80)
        print("📊 EMERGENCY RETRAIN SUMMARY:")

        retrained = sum(1 for r in results if r['retrain_status'] == 'deployed')
        skipped = sum(1 for r in results if r['retrain_status'] == 'skipped')
        not_needed = sum(1 for r in results if r['retrain_status'] == 'not_needed')

        print(f"   Total evaluated: {len(results)}")
        print(f"   🔄 Retrained: {retrained}")
        print(f"   ⏭️ Skipped: {skipped}")
        print(f"   ✅ Not needed: {not_needed}")

        return results


def main():
    parser = argparse.ArgumentParser(description='Emergency retraining system')
    parser.add_argument('--auto', action='store_true',
                        help='Auto check and retrain if needed')
    parser.add_argument('--check', action='store_true',
                        help='Check status only (no retrain)')
    parser.add_argument('--force', action='store_true',
                        help='Force retrain without checking')
    parser.add_argument('--tickers', type=str, default='VCB',
                        help='Comma-separated tickers (e.g., VCB,HPG,VHM)')
    parser.add_argument('--horizons', type=str, default='3day',
                        help='Comma-separated horizons (e.g., 3day,48day)')

    args = parser.parse_args()

    tickers = [t.strip() for t in args.tickers.split(',')]
    horizons = [h.strip() for h in args.horizons.split(',')]

    system = EmergencyRetrainingSystem()

    if args.check:
        # Check only mode
        print("🔍 CHECK MODE - Evaluating models without retraining\n")

        for ticker in tickers:
            for horizon in horizons:
                system.evaluate_ticker(ticker, horizon)

    elif args.force:
        # Force retrain mode
        print("⚠️ FORCE MODE - Retraining without evaluation\n")

        # TODO: Implement force retrain
        print("Not implemented yet. Use --auto instead.")

    elif args.auto:
        # Auto mode: Evaluate and retrain if needed
        system.emergency_retrain(tickers, horizons)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
