"""
PatchTST model for stock price prediction
Simplified version for production
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from .base_model import BaseModel


class PatchTSTModel(BaseModel):
    """
    Simplified PatchTST (Patch Time Series Transformer)

    Strengths:
    - SOTA for time series forecasting
    - Patching reduces complexity
    - Channel independence
    - Long-range dependencies
    """

    def __init__(self, params: dict = None):
        super().__init__(model_name='PatchTST')

        # Default parameters
        self.params = params or {
            'seq_len': 96,      # Look back 96 days
            'patch_len': 16,    # Patch size
            'stride': 8,        # Patch stride
            'd_model': 128,     # Model dimension
            'n_heads': 8,       # Attention heads
            'n_layers': 3,      # Transformer layers
            'd_ff': 256,        # Feedforward dimension
            'dropout': 0.2,
            'learning_rate': 0.0001,
            'epochs': 100,
            'batch_size': 32,
            'patience': 10
        }

        self.n_features = None
        self.num_patch = int(
            (self.params['seq_len'] - self.params['patch_len']) / self.params['stride'] + 1
        )

    def _build_model(self):
        """Build PatchTST model"""
        # Input: (batch, seq_len, n_features)
        inputs = keras.Input(shape=(self.params['seq_len'], self.n_features))

        # Patching layer (simplified - using Conv1D)
        # Shape: (batch, num_patches, patch_len * n_features)
        x = layers.Conv1D(
            filters=self.params['d_model'],
            kernel_size=self.params['patch_len'],
            strides=self.params['stride'],
            padding='valid'
        )(inputs)

        # Positional encoding
        positions = tf.range(start=0, limit=self.num_patch, delta=1)
        pos_encoding = layers.Embedding(
            input_dim=self.num_patch,
            output_dim=self.params['d_model']
        )(positions)
        x = x + pos_encoding

        # Transformer encoder layers
        for _ in range(self.params['n_layers']):
            # Multi-head attention
            attention_out = layers.MultiHeadAttention(
                num_heads=self.params['n_heads'],
                key_dim=self.params['d_model'] // self.params['n_heads']
            )(x, x)
            attention_out = layers.Dropout(self.params['dropout'])(attention_out)
            x = layers.LayerNormalization()(x + attention_out)

            # Feedforward network
            ff = layers.Dense(self.params['d_ff'], activation='relu')(x)
            ff = layers.Dropout(self.params['dropout'])(ff)
            ff = layers.Dense(self.params['d_model'])(ff)
            x = layers.LayerNormalization()(x + ff)

        # Global average pooling
        x = layers.GlobalAveragePooling1D()(x)

        # Output layer
        x = layers.Dense(128, activation='relu')(x)
        x = layers.Dropout(self.params['dropout'])(x)
        outputs = layers.Dense(1)(x)

        # Create model
        model = keras.Model(inputs=inputs, outputs=outputs)

        # Compile
        model.compile(
            optimizer=keras.optimizers.Adam(self.params['learning_rate']),
            loss='mse',
            metrics=['mae']
        )

        return model

    def _create_sequences(self, X: np.ndarray, y: np.ndarray):
        """Create sequences for PatchTST"""
        X_seq, y_seq = [], []

        for i in range(self.params['seq_len'], len(X)):
            X_seq.append(X[i - self.params['seq_len']:i])
            y_seq.append(y[i])

        return np.array(X_seq), np.array(y_seq)

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'PatchTSTModel':
        """
        Train PatchTST model

        Args:
            X: Features
            y: Targets

        Returns:
            self
        """
        self.n_features = X.shape[1]

        # Create sequences
        X_seq, y_seq = self._create_sequences(X, y)

        # Build model
        self.model = self._build_model()

        # Train
        self.model.fit(
            X_seq, y_seq,
            epochs=self.params['epochs'],
            batch_size=self.params['batch_size'],
            validation_split=0.1,
            callbacks=[
                keras.callbacks.EarlyStopping(
                    patience=self.params['patience'],
                    restore_best_weights=True
                ),
                keras.callbacks.ReduceLROnPlateau(
                    factor=0.5,
                    patience=5
                )
            ],
            verbose=0
        )

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict using PatchTST

        Args:
            X: Features

        Returns:
            Predictions
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet. Call fit() first.")

        # Create sequences
        if len(X.shape) == 2:
            X_seq = []
            for i in range(self.params['seq_len'], len(X) + 1):
                if i <= len(X):
                    X_seq.append(X[max(0, i - self.params['seq_len']):i])

            if len(X_seq) == 0:
                # Pad with zeros if not enough data
                X_seq = np.zeros((1, self.params['seq_len'], self.n_features))
                X_seq[0, -len(X):] = X
            else:
                X_seq = np.array(X_seq)
        else:
            X_seq = X

        predictions = self.model.predict(X_seq, verbose=0)
        return predictions.flatten()
