"""
Retraining Scheduler for Ensemble Models

This script handles:
1. Check if model needs retraining
2. Retrain models on schedule (weekly/monthly)
3. Compare old vs new model performance
4. Auto-deploy if new model is better

Usage:
    python scripts/retrain_scheduler.py --mode check
    python scripts/retrain_scheduler.py --mode retrain --tickers VCB,VHM
    python scripts/retrain_scheduler.py --mode auto  # Auto retrain if needed
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import argparse
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pickle

from prediction.ensemble_stacking import EnsembleStacking
from prediction.utils.feature_engineering import create_features, prepare_training_data


class RetrainingScheduler:
    """
    Scheduler for automatic model retraining

    Strategies:
    1. Time-based: Retrain every N days
    2. Performance-based: Retrain if accuracy drops
    3. Data-based: Retrain when N% new data accumulated
    """

    def __init__(self, models_dir: str = 'src/prediction/trained_models'):
        self.models_dir = models_dir
        self.metadata_file = os.path.join(models_dir, 'retraining_metadata.json')

    def should_retrain(
        self,
        ticker: str,
        horizon: str,
        strategy: str = 'time',
        **kwargs
    ) -> tuple[bool, str]:
        """
        Check if model should be retrained

        Args:
            ticker: Stock ticker
            horizon: '3day' or '48day'
            strategy: 'time', 'performance', or 'data'
            **kwargs: Strategy-specific parameters

        Returns:
            (should_retrain: bool, reason: str)
        """
        model_path = os.path.join(self.models_dir, f"{ticker}_{horizon}_ensemble.pkl")

        # Check if model exists
        if not os.path.exists(model_path):
            return True, "Model does not exist"

        # Get model age
        model_modified = datetime.fromtimestamp(os.path.getmtime(model_path))
        days_old = (datetime.now() - model_modified).days

        if strategy == 'time':
            # Time-based: Retrain every N days
            retrain_interval = kwargs.get('retrain_interval_days', 7)  # Default: weekly

            if days_old >= retrain_interval:
                return True, f"Model is {days_old} days old (threshold: {retrain_interval})"
            else:
                return False, f"Model is fresh ({days_old} days old)"

        elif strategy == 'performance':
            # Performance-based: Retrain if recent predictions are inaccurate
            # This requires tracking prediction accuracy

            # TODO: Implement performance tracking
            # - Store predictions in database
            # - Compare with actual prices
            # - Calculate recent MAPE
            # - Retrain if MAPE > threshold

            return False, "Performance tracking not yet implemented"

        elif strategy == 'data':
            # Data-based: Retrain when N% new data accumulated
            new_data_threshold = kwargs.get('new_data_threshold', 0.05)  # 5% new data

            # Load model to check training data size
            with open(model_path, 'rb') as f:
                ensemble = pickle.load(f)

            # Get metadata (if available)
            if hasattr(ensemble, 'training_metadata'):
                training_data_size = ensemble.training_metadata.get('n_samples', 1000)
            else:
                training_data_size = 1000  # Assume default

            # New data = days since last training
            new_data_size = days_old
            new_data_ratio = new_data_size / training_data_size

            if new_data_ratio >= new_data_threshold:
                return True, f"New data ratio: {new_data_ratio:.2%} (threshold: {new_data_threshold:.2%})"
            else:
                return False, f"Not enough new data: {new_data_ratio:.2%}"

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def retrain_model(
        self,
        ticker: str,
        horizon: str,
        data: pd.DataFrame,
        compare_with_old: bool = True
    ) -> Dict:
        """
        Retrain model and optionally compare with old model

        Args:
            ticker: Stock ticker
            horizon: '3day' or '48day'
            data: Training data (OHLCV)
            compare_with_old: If True, compare with old model

        Returns:
            Dictionary with retraining results
        """
        print(f"\n{'='*80}")
        print(f"🔄 RETRAINING: {ticker} ({horizon})")
        print(f"{'='*80}")

        result = {
            'ticker': ticker,
            'horizon': horizon,
            'retrain_date': datetime.now().isoformat(),
            'status': 'pending'
        }

        # Prepare training data
        print(f"📊 Data size: {len(data)} days")
        features = create_features(data)

        horizon_days = int(horizon.replace('day', ''))
        X_train, X_test, y_train, y_test = prepare_training_data(
            features,
            horizon=horizon_days,
            test_size=0.2
        )

        print(f"   Train: {len(X_train)} samples")
        print(f"   Test:  {len(X_test)} samples")

        # Load old model for comparison (if exists)
        old_model_path = os.path.join(self.models_dir, f"{ticker}_{horizon}_ensemble.pkl")
        old_model = None
        old_mape = None

        if compare_with_old and os.path.exists(old_model_path):
            print(f"\n📂 Loading old model for comparison...")
            try:
                old_model = EnsembleStacking.load(old_model_path)

                # Evaluate old model
                y_pred_old = old_model.predict(X_test)
                old_mape = (abs(y_pred_old - y_test) / y_test).mean() * 100
                print(f"   Old model MAPE: {old_mape:.3f}%")

                result['old_mape'] = old_mape

            except Exception as e:
                print(f"   ⚠️ Could not load old model: {e}")

        # Train new model
        print(f"\n🏋️ Training new ensemble...")
        ensemble = EnsembleStacking(n_folds=5)
        ensemble.fit(X_train, y_train)

        # Evaluate new model
        y_pred_new = ensemble.predict(X_test)
        new_mape = (abs(y_pred_new - y_test) / y_test).mean() * 100

        print(f"\n📊 NEW MODEL RESULTS:")
        print(f"   MAPE: {new_mape:.3f}%")

        # Get metrics from ensemble
        metrics = ensemble.get_metrics_summary()
        print(f"\n   Base models performance:")
        for _, row in metrics.iterrows():
            print(f"   - {row['model']}: MAPE {row['mape']:.3f}% | R² {row['r2']:.3f}")

        result['new_mape'] = new_mape
        result['metrics'] = metrics.to_dict('records')

        # Compare with old model
        if old_mape is not None:
            improvement = old_mape - new_mape
            improvement_pct = (improvement / old_mape) * 100

            print(f"\n🔍 COMPARISON:")
            print(f"   Old MAPE: {old_mape:.3f}%")
            print(f"   New MAPE: {new_mape:.3f}%")
            print(f"   Improvement: {improvement:+.3f}% ({improvement_pct:+.1f}%)")

            result['improvement'] = improvement
            result['improvement_pct'] = improvement_pct

            # Decision: Deploy new model?
            if new_mape < old_mape:
                decision = "✅ DEPLOY - New model is better"
                should_deploy = True
            elif new_mape < old_mape * 1.05:  # Within 5% of old
                decision = "⚠️ DEPLOY - New model is similar (acceptable)"
                should_deploy = True
            else:
                decision = "❌ DO NOT DEPLOY - New model is worse"
                should_deploy = False

            print(f"\n   Decision: {decision}")
            result['should_deploy'] = should_deploy
            result['decision'] = decision

        else:
            # No old model, always deploy
            should_deploy = True
            result['should_deploy'] = True
            result['decision'] = "✅ DEPLOY - First model"

        # Save new model
        if should_deploy:
            # Backup old model
            if os.path.exists(old_model_path):
                backup_path = old_model_path.replace('.pkl', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pkl')
                os.rename(old_model_path, backup_path)
                print(f"\n💾 Old model backed up to: {backup_path}")

            # Save new model
            ensemble.save(old_model_path)
            print(f"💾 New model saved to: {old_model_path}")
            result['status'] = 'deployed'
        else:
            # Save as candidate (don't overwrite)
            candidate_path = old_model_path.replace('.pkl', f'_candidate_{datetime.now().strftime("%Y%m%d")}.pkl')
            ensemble.save(candidate_path)
            print(f"\n💾 New model saved as candidate: {candidate_path}")
            print(f"   (Not deployed because performance is worse)")
            result['status'] = 'candidate'
            result['candidate_path'] = candidate_path

        print(f"{'='*80}\n")

        return result

    def auto_retrain(
        self,
        tickers: List[str],
        horizons: List[str] = ['3day', '48day'],
        strategy: str = 'time',
        retrain_interval_days: int = 7
    ):
        """
        Automatically check and retrain models that need updating

        Args:
            tickers: List of tickers to check
            horizons: List of horizons to check
            strategy: Retraining strategy
            retrain_interval_days: Days between retraining
        """
        print("🤖 AUTO RETRAINING MODE")
        print("="*80)

        results = []

        for ticker in tickers:
            for horizon in horizons:
                print(f"\n📋 Checking: {ticker} ({horizon})")

                # Check if retraining is needed
                should_retrain, reason = self.should_retrain(
                    ticker,
                    horizon,
                    strategy=strategy,
                    retrain_interval_days=retrain_interval_days
                )

                print(f"   {reason}")

                if should_retrain:
                    print(f"   → Retraining...")

                    # Load data
                    # TODO: Replace with actual data loading
                    # from database.connection import get_connection
                    # data = load_stock_data(ticker)

                    print(f"   ⚠️ Skipping: Need to implement data loading")
                    results.append({
                        'ticker': ticker,
                        'horizon': horizon,
                        'status': 'skipped',
                        'reason': 'data loading not implemented'
                    })
                else:
                    print(f"   → No retraining needed")
                    results.append({
                        'ticker': ticker,
                        'horizon': horizon,
                        'status': 'skipped',
                        'reason': reason
                    })

        print("\n" + "="*80)
        print("📊 SUMMARY:")
        for r in results:
            print(f"   {r['ticker']} ({r['horizon']}): {r['status']} - {r.get('reason', 'N/A')}")

        return results


def main():
    parser = argparse.ArgumentParser(description='Retrain ensemble models')
    parser.add_argument('--mode', choices=['check', 'retrain', 'auto'], required=True,
                        help='Mode: check, retrain, or auto')
    parser.add_argument('--tickers', type=str, default='VCB',
                        help='Comma-separated list of tickers (e.g., VCB,VHM,HPG)')
    parser.add_argument('--horizons', type=str, default='3day,48day',
                        help='Comma-separated list of horizons')
    parser.add_argument('--strategy', choices=['time', 'performance', 'data'], default='time',
                        help='Retraining strategy')
    parser.add_argument('--interval', type=int, default=7,
                        help='Retraining interval in days (for time strategy)')

    args = parser.parse_args()

    tickers = [t.strip() for t in args.tickers.split(',')]
    horizons = [h.strip() for h in args.horizons.split(',')]

    scheduler = RetrainingScheduler()

    if args.mode == 'check':
        print("🔍 CHECKING RETRAINING STATUS\n")

        for ticker in tickers:
            for horizon in horizons:
                should_retrain, reason = scheduler.should_retrain(
                    ticker, horizon,
                    strategy=args.strategy,
                    retrain_interval_days=args.interval
                )

                status = "🔄 NEEDS RETRAINING" if should_retrain else "✅ UP TO DATE"
                print(f"{ticker} ({horizon}): {status}")
                print(f"   Reason: {reason}\n")

    elif args.mode == 'retrain':
        print("🏋️ MANUAL RETRAINING\n")
        print("⚠️ Note: You need to implement data loading first\n")

        # TODO: Implement data loading and call retrain_model()

    elif args.mode == 'auto':
        scheduler.auto_retrain(
            tickers=tickers,
            horizons=horizons,
            strategy=args.strategy,
            retrain_interval_days=args.interval
        )


if __name__ == '__main__':
    main()
