"""
Ensemble Stacking for maximum prediction accuracy
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from sklearn.model_selection import KFold
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
import pickle
from pathlib import Path

from .models import (
    LightGBMModel,
    ProphetModel,
    XGBoostModel,
    LSTMModel,
    PatchTSTModel
)


class EnsembleStacking:
    """
    Stacking Ensemble of 5 models for maximum accuracy

    Models:
    1. PatchTST - Transformer-based, SOTA
    2. LightGBM - Fast, non-linear patterns
    3. LSTM + Attention - Sequential dependencies
    4. Prophet - Trend detection
    5. XGBoost - Complex relationships

    Architecture:
        Level 1: 5 base models (trained with CV)
        Level 2: Meta-model (Neural Network)
    """

    def __init__(self, n_folds: int = 5, random_state: int = 42):
        """
        Initialize Ensemble Stacking

        Args:
            n_folds: Number of folds for cross-validation
            random_state: Random seed
        """
        self.n_folds = n_folds
        self.random_state = random_state

        # Initialize 5 base models
        self.base_models = {
            'patchtst': PatchTSTModel(),
            'lightgbm': LightGBMModel(),
            'lstm': LSTMModel(),
            'prophet': ProphetModel(),
            'xgboost': XGBoostModel()
        }

        # Meta-model (learns how to combine predictions)
        self.meta_model = MLPRegressor(
            hidden_layer_sizes=(64, 32),
            activation='relu',
            max_iter=1000,
            early_stopping=True,
            validation_fraction=0.1,
            random_state=random_state,
            verbose=False
        )

        self.is_fitted = False
        self.model_weights = None
        self.training_metrics = {}

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'EnsembleStacking':
        """
        Train ensemble with stacking

        Args:
            X: Features, shape (n_samples, n_features)
            y: Targets, shape (n_samples,)

        Returns:
            self
        """
        print("=" * 60)
        print("ENSEMBLE STACKING TRAINING")
        print("=" * 60)
        print(f"Training data: {X.shape[0]} samples, {X.shape[1]} features")
        print(f"Cross-validation: {self.n_folds} folds")
        print(f"Base models: {len(self.base_models)}")
        print()

        # Step 1: Train base models with cross-validation
        meta_features = self._train_base_models_cv(X, y)

        # Step 2: Train meta-model
        print("\n" + "=" * 60)
        print("TRAINING META-MODEL")
        print("=" * 60)
        self.meta_model.fit(meta_features, y)
        print("✓ Meta-model trained")

        # Step 3: Evaluate ensemble
        final_predictions = self.meta_model.predict(meta_features)
        self._evaluate_ensemble(y, final_predictions, meta_features)

        # Step 4: Analyze model contributions
        self._analyze_model_contributions(meta_features, y)

        self.is_fitted = True
        print("\n✅ Ensemble Stacking training completed!")

        return self

    def _train_base_models_cv(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        Train base models with cross-validation

        Returns:
            meta_features: shape (n_samples, n_models)
        """
        n_samples = X.shape[0]
        n_models = len(self.base_models)
        meta_features = np.zeros((n_samples, n_models))

        kf = KFold(n_splits=self.n_folds, shuffle=True, random_state=self.random_state)

        for i, (model_name, model) in enumerate(self.base_models.items()):
            print("\n" + "-" * 60)
            print(f"Training Model {i + 1}/{n_models}: {model_name.upper()}")
            print("-" * 60)

            # Out-of-fold predictions
            oof_predictions = np.zeros(n_samples)

            # Cross-validation
            for fold, (train_idx, val_idx) in enumerate(kf.split(X)):
                print(f"  Fold {fold + 1}/{self.n_folds}...", end=" ", flush=True)

                X_train_fold = X[train_idx]
                y_train_fold = y[train_idx]
                X_val_fold = X[val_idx]

                try:
                    # Train on fold
                    if model_name == 'patchtst':
                        model_fold = PatchTSTModel()
                    elif model_name == 'lightgbm':
                        model_fold = LightGBMModel()
                    elif model_name == 'lstm':
                        model_fold = LSTMModel()
                    elif model_name == 'prophet':
                        model_fold = ProphetModel()
                    else:  # xgboost
                        model_fold = XGBoostModel()

                    model_fold.fit(X_train_fold, y_train_fold)

                    # Predict on validation fold
                    val_predictions = model_fold.predict(X_val_fold)
                    oof_predictions[val_idx] = val_predictions

                    print("✓")

                except Exception as e:
                    print(f"✗ (Error: {str(e)[:50]}...)")
                    # Fill with mean if model fails
                    oof_predictions[val_idx] = np.mean(y_train_fold)

            # Store out-of-fold predictions as meta-features
            meta_features[:, i] = oof_predictions

            # Train final model on full data
            print(f"  Training {model_name} on full data...", end=" ", flush=True)
            try:
                model.fit(X, y)
                print("✓")
            except Exception as e:
                print(f"✗ (Error: {str(e)[:50]}...)")

            # Evaluate this model
            mape = mean_absolute_percentage_error(y, oof_predictions)
            mae = mean_absolute_error(y, oof_predictions)
            r2 = r2_score(y, oof_predictions)

            self.training_metrics[model_name] = {
                'mape': mape * 100,
                'mae': mae,
                'r2': r2
            }

            print(f"  ✓ {model_name.upper()} CV Metrics:")
            print(f"      MAPE: {mape * 100:.2f}%")
            print(f"      MAE:  {mae:.4f}")
            print(f"      R²:   {r2:.4f}")

        return meta_features

    def _evaluate_ensemble(self, y_true: np.ndarray, y_pred: np.ndarray, meta_features: np.ndarray):
        """Evaluate ensemble performance"""
        mape = mean_absolute_percentage_error(y_true, y_pred)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)

        print("\n" + "=" * 60)
        print("ENSEMBLE PERFORMANCE")
        print("=" * 60)
        print(f"MAPE: {mape * 100:.2f}%")
        print(f"MAE:  {mae:.4f}")
        print(f"R²:   {r2:.4f}")

        # Compare with best single model
        best_single_model = min(self.training_metrics.items(), key=lambda x: x[1]['mape'])
        improvement = best_single_model[1]['mape'] - (mape * 100)

        print(f"\nBest single model: {best_single_model[0].upper()} (MAPE: {best_single_model[1]['mape']:.2f}%)")
        print(f"Ensemble improvement: {improvement:+.2f}% ({improvement / best_single_model[1]['mape'] * 100:.1f}%)")

    def _analyze_model_contributions(self, meta_features: np.ndarray, y_true: np.ndarray):
        """Analyze how much each model contributes"""
        print("\n" + "=" * 60)
        print("MODEL CONTRIBUTION ANALYSIS")
        print("=" * 60)

        # Extract weights from meta-model (first layer)
        if hasattr(self.meta_model, 'coefs_'):
            first_layer_weights = self.meta_model.coefs_[0]
            # Average absolute weights across hidden units
            avg_weights = np.abs(first_layer_weights).mean(axis=1)
            # Normalize to sum = 1
            self.model_weights = avg_weights / avg_weights.sum()

            print("Learned Weights (from Meta-Model):")
            for i, (model_name, weight) in enumerate(zip(self.base_models.keys(), self.model_weights)):
                bar = "█" * int(weight * 50)
                print(f"  {model_name:12} | {weight:.3f} | {bar}")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict using stacked ensemble

        Args:
            X: Features, shape (n_samples, n_features)

        Returns:
            Predictions, shape (n_samples,)
        """
        if not self.is_fitted:
            raise ValueError("Ensemble is not fitted yet. Call fit() first.")

        # Step 1: Get predictions from all base models
        n_samples = X.shape[0]
        n_models = len(self.base_models)
        meta_features = np.zeros((n_samples, n_models))

        for i, (model_name, model) in enumerate(self.base_models.items()):
            try:
                meta_features[:, i] = model.predict(X)
            except Exception as e:
                print(f"Warning: {model_name} prediction failed: {e}")
                # Use mean of other models
                meta_features[:, i] = meta_features[:, :i].mean(axis=1) if i > 0 else np.zeros(n_samples)

        # Step 2: Meta-model combines predictions
        final_predictions = self.meta_model.predict(meta_features)

        return final_predictions

    def save(self, filepath: str):
        """Save ensemble to disk"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'wb') as f:
            pickle.dump(self, f)

        print(f"✓ Ensemble saved to {filepath}")

    @staticmethod
    def load(filepath: str) -> 'EnsembleStacking':
        """Load ensemble from disk"""
        with open(filepath, 'rb') as f:
            ensemble = pickle.load(f)

        print(f"✓ Ensemble loaded from {filepath}")
        return ensemble

    def get_metrics_summary(self) -> pd.DataFrame:
        """Get summary of all model metrics"""
        if not self.training_metrics:
            return None

        df = pd.DataFrame(self.training_metrics).T
        df['weight'] = self.model_weights if self.model_weights is not None else 0
        df = df.sort_values('mape')

        return df
