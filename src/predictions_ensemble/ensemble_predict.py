"""
Ensemble Stock Price Predictor
Combines ARIMAX + XGBoost for best results
- ARIMAX: Provides confidence intervals, interpretable
- XGBoost: Provides accuracy, CPU-friendly, fast
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EnsemblePredictor:
    """
    Ensemble predictor combining ARIMAX + XGBoost

    Strategy:
    - ARIMAX: 40% weight (provides CI, stable baseline)
    - XGBoost: 60% weight (provides accuracy, pattern detection)
    - Fallback: If either fails, use the other
    """

    @staticmethod
    def predict_3day_ensemble(df, weights=None):
        """
        Predict 3 days using ARIMAX + XGBoost ensemble

        Args:
            df: DataFrame với stock data
            weights: Dict {'arimax': float, 'xgboost': float} (default: 0.4, 0.6)

        Returns:
            dict: {
                'predictions': [day1, day2, day3],
                'confidence_interval': {'lower': [...], 'upper': [...]},
                'components': {'arimax': [...], 'xgboost': [...]},
                'weights': {...},
                'model': 'ENSEMBLE'
            }
        """
        if weights is None:
            weights = {'arimax': 0.4, 'xgboost': 0.6}

        try:
            from src.predictions_arima.arimax_predict import ARIMAXPredictor
            from src.predictions_xgboost.xgboost_predict import XGBoostPredictor

            logger.info("🔮 Starting Ensemble Prediction...")
            start_time = datetime.now()

            # Component 1: ARIMAX (with confidence interval)
            logger.info("🟣 Running ARIMAX component...")
            arimax_start = datetime.now()
            arimax_result = ARIMAXPredictor.predict_with_confidence(df)
            arimax_time = (datetime.now() - arimax_start).total_seconds()

            if arimax_result:
                logger.info(f"✅ ARIMAX completed in {arimax_time:.2f}s")
                logger.info(f"   Predictions: {arimax_result['predictions']}")
            else:
                logger.warning("⚠️ ARIMAX failed")

            # Component 2: XGBoost
            logger.info("🔵 Running XGBoost component...")
            xgb_start = datetime.now()
            xgb_result = XGBoostPredictor.predict_with_metrics(df, steps=3)
            xgb_time = (datetime.now() - xgb_start).total_seconds()

            if xgb_result:
                logger.info(f"✅ XGBoost completed in {xgb_time:.2f}s")
                logger.info(f"   Predictions: {xgb_result['predictions']}")
                logger.info(f"   MAE: {xgb_result['mae']:.2f}")
            else:
                logger.warning("⚠️ XGBoost failed")

            # Ensemble logic
            if arimax_result and xgb_result:
                # Both models succeeded - weighted ensemble
                arimax_pred = arimax_result['predictions']
                xgb_pred = xgb_result['predictions']

                final_predictions = [
                    weights['arimax'] * arimax_pred[i] + weights['xgboost'] * xgb_pred[i]
                    for i in range(3)
                ]
                final_predictions = [round(p, 2) for p in final_predictions]

                total_time = (datetime.now() - start_time).total_seconds()

                result = {
                    'predictions': final_predictions,
                    'confidence_interval': {
                        'lower': arimax_result['lower_bound'],
                        'upper': arimax_result['upper_bound']
                    },
                    'components': {
                        'arimax': arimax_pred,
                        'xgboost': xgb_pred
                    },
                    'weights': weights,
                    'timing': {
                        'arimax': arimax_time,
                        'xgboost': xgb_time,
                        'total': total_time
                    },
                    'features_used': {
                        'arimax': arimax_result['features_used'],
                        'xgboost': xgb_result['features_used']
                    },
                    'model': 'ENSEMBLE_ARIMAX_XGBOOST'
                }

                logger.info(f"✅ Ensemble completed in {total_time:.2f}s")
                logger.info(f"   Final predictions: {final_predictions}")

                return result

            elif arimax_result:
                # Only ARIMAX succeeded
                logger.warning("⚠️ Using ARIMAX only (XGBoost failed)")
                return {
                    'predictions': arimax_result['predictions'],
                    'confidence_interval': {
                        'lower': arimax_result['lower_bound'],
                        'upper': arimax_result['upper_bound']
                    },
                    'components': {'arimax': arimax_result['predictions']},
                    'model': 'ARIMAX_FALLBACK'
                }

            elif xgb_result:
                # Only XGBoost succeeded
                logger.warning("⚠️ Using XGBoost only (ARIMAX failed)")
                return {
                    'predictions': xgb_result['predictions'],
                    'confidence_interval': None,
                    'components': {'xgboost': xgb_result['predictions']},
                    'model': 'XGBOOST_FALLBACK'
                }

            else:
                # Both failed
                logger.error("❌ Both ARIMAX and XGBoost failed")
                return None

        except Exception as e:
            logger.error(f"❌ Ensemble prediction error: {e}", exc_info=True)
            return None

    @staticmethod
    def predict_with_comparison(df):
        """
        Predict và show comparison giữa các models

        Args:
            df: DataFrame

        Returns:
            dict: Results with detailed comparison
        """
        try:
            from src.predictions.simple_predict import SimplePredictor

            logger.info("\\n" + "="*60)
            logger.info("📊 ENSEMBLE PREDICTION WITH COMPARISON")
            logger.info("="*60 + "\\n")

            last_price = df['close'].iloc[-1]
            logger.info(f"📌 Last price: {last_price:,.2f}đ\\n")

            # Get MA prediction (baseline)
            logger.info("🔵 MA Prediction...")
            ma_pred = SimplePredictor.predict_3day_ma(df)

            # Get Ensemble prediction
            ensemble_result = EnsemblePredictor.predict_3day_ensemble(df)

            if ensemble_result and ma_pred:
                logger.info("\\n" + "="*60)
                logger.info("📊 COMPARISON RESULTS")
                logger.info("="*60 + "\\n")

                # Print comparison table
                logger.info("Model Predictions:")
                for day in range(3):
                    logger.info(f"\\n  Day {day+1}:")
                    logger.info(f"    MA:       {ma_pred[day]:,.2f}đ")

                    if 'arimax' in ensemble_result['components']:
                        logger.info(f"    ARIMAX:   {ensemble_result['components']['arimax'][day]:,.2f}đ")

                    if 'xgboost' in ensemble_result['components']:
                        logger.info(f"    XGBoost:  {ensemble_result['components']['xgboost'][day]:,.2f}đ")

                    logger.info(f"    ENSEMBLE: {ensemble_result['predictions'][day]:,.2f}đ")

                    # Confidence interval
                    if ensemble_result.get('confidence_interval'):
                        ci = ensemble_result['confidence_interval']
                        logger.info(f"    95% CI:   [{ci['lower'][day]:,.2f}, {ci['upper'][day]:,.2f}]")

                # Timing
                logger.info("\\n  Timing:")
                if 'timing' in ensemble_result:
                    timing = ensemble_result['timing']
                    logger.info(f"    ARIMAX:   {timing.get('arimax', 0):.2f}s")
                    logger.info(f"    XGBoost:  {timing.get('xgboost', 0):.2f}s")
                    logger.info(f"    Total:    {timing.get('total', 0):.2f}s")

                return {
                    'ma': ma_pred,
                    'ensemble': ensemble_result,
                    'last_price': last_price
                }

            return None

        except Exception as e:
            logger.error(f"❌ Error in comparison: {e}")
            return None

    @staticmethod
    def optimize_weights(df, validation_days=30):
        """
        Tự động optimize weights cho ensemble

        Args:
            df: DataFrame (cần nhiều data để validate)
            validation_days: Số ngày dùng để validate

        Returns:
            dict: Optimal weights
        """
        try:
            from src.predictions_arima.arimax_predict import ARIMAXPredictor
            from src.predictions_xgboost.xgboost_predict import XGBoostPredictor
            from sklearn.metrics import mean_absolute_error

            if len(df) < validation_days + 60:
                logger.warning(f"⚠️ Not enough data for weight optimization")
                return {'arimax': 0.4, 'xgboost': 0.6}

            logger.info(f"🔧 Optimizing ensemble weights using {validation_days} days validation...")

            # Split data
            train_df = df.iloc[:-validation_days]
            val_df = df.iloc[-validation_days:]

            # Test different weight combinations
            best_mae = float('inf')
            best_weights = None

            weight_combinations = [
                {'arimax': 0.2, 'xgboost': 0.8},
                {'arimax': 0.3, 'xgboost': 0.7},
                {'arimax': 0.4, 'xgboost': 0.6},
                {'arimax': 0.5, 'xgboost': 0.5},
                {'arimax': 0.6, 'xgboost': 0.4},
            ]

            for weights in weight_combinations:
                predictions = []
                actuals = []

                # Validate on each day
                for i in range(len(val_df) - 3):
                    current_df = pd.concat([train_df, val_df.iloc[:i+1]])

                    # Predict
                    arimax_result = ARIMAXPredictor.predict_3day_arimax(current_df)
                    xgb_result = XGBoostPredictor.predict_3day_xgboost(current_df)

                    if arimax_result and xgb_result:
                        arimax_pred = arimax_result['predictions']
                        ensemble_pred = [
                            weights['arimax'] * arimax_pred[j] + weights['xgboost'] * xgb_result[j]
                            for j in range(3)
                        ]

                        predictions.append(ensemble_pred[0])  # Day 1 prediction
                        actuals.append(val_df.iloc[i+1]['close'])  # Actual next day

                # Calculate MAE
                if len(predictions) > 0:
                    mae = mean_absolute_error(actuals, predictions)
                    logger.info(f"   Weights {weights}: MAE = {mae:.2f}")

                    if mae < best_mae:
                        best_mae = mae
                        best_weights = weights

            logger.info(f"✅ Optimal weights: {best_weights} (MAE: {best_mae:.2f})")
            return best_weights

        except Exception as e:
            logger.error(f"❌ Error optimizing weights: {e}")
            return {'arimax': 0.4, 'xgboost': 0.6}

    @staticmethod
    def batch_predict(tickers_data: dict, weights=None):
        """
        Predict nhiều tickers cùng lúc

        Args:
            tickers_data: Dict {ticker: dataframe}
            weights: Ensemble weights

        Returns:
            dict: {ticker: predictions}
        """
        results = {}

        for ticker, df in tickers_data.items():
            logger.info(f"\\n🔄 Processing {ticker}...")
            result = EnsemblePredictor.predict_3day_ensemble(df, weights=weights)

            if result:
                results[ticker] = result
            else:
                logger.warning(f"⚠️ Failed to predict {ticker}")

        logger.info(f"\\n✅ Batch prediction completed: {len(results)}/{len(tickers_data)} successful")
        return results
