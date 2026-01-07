"""
LSTM model with Attention for stock price prediction
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from .base_model import BaseModel


class LSTMModel(BaseModel):
    """
    LSTM with Multi-Head Attention

    Strengths:
    - Captures temporal dependencies
    - Memory of past sequences
    - Attention focuses on important timesteps
    """

    def __init__(self, params: dict = None):
        super().__init__(model_name='LSTM')

        # Default parameters
        self.params = params or {
            'lstm_units': [128, 64],
            'd_model': 64,
            'n_heads': 8,
            'dropout': 0.2,
            'learning_rate': 0.001,
            'epochs': 100,
            'batch_size': 32,
            'patience': 10
        }

        self.seq_len = 60  # Look back 60 days
        self.n_features = None

    def _build_model(self):
        """Build LSTM + Attention model"""
        # Input layer
        inputs = keras.Input(shape=(self.seq_len, self.n_features))

        # Bidirectional LSTM layers
        x = inputs
        for units in self.params['lstm_units']:
            x = layers.Bidirectional(
                layers.LSTM(units, return_sequences=True)
            )(x)
            x = layers.Dropout(self.params['dropout'])(x)

        # Multi-Head Attention
        attention_out = layers.MultiHeadAttention(
            num_heads=self.params['n_heads'],
            key_dim=self.params['d_model']
        )(x, x)
        attention_out = layers.Dropout(0.1)(attention_out)
        x = layers.LayerNormalization()(x + attention_out)

        # Take last timestep
        x = layers.Lambda(lambda x: x[:, -1, :])(x)

        # Dense layers
        x = layers.Dense(128, activation='relu')(x)
        x = layers.Dropout(self.params['dropout'])(x)
        outputs = layers.Dense(1)(x)  # Single output (price)

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
        """
        Create sequences for LSTM

        Args:
            X: Features (n_samples, n_features)
            y: Targets (n_samples,)

        Returns:
            X_seq, y_seq
        """
        X_seq, y_seq = [], []

        for i in range(self.seq_len, len(X)):
            X_seq.append(X[i - self.seq_len:i])
            y_seq.append(y[i])

        return np.array(X_seq), np.array(y_seq)

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'LSTMModel':
        """
        Train LSTM model

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
        Predict using LSTM

        Args:
            X: Features

        Returns:
            Predictions
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet. Call fit() first.")

        # For inference, we need to create sequences
        # Assuming X is already in correct format or handle it
        if len(X.shape) == 2:
            # Need to create sequences
            X_seq = []
            for i in range(self.seq_len, len(X) + 1):
                if i <= len(X):
                    X_seq.append(X[max(0, i - self.seq_len):i])

            if len(X_seq) == 0:
                # Not enough data, pad with zeros
                X_seq = np.zeros((1, self.seq_len, self.n_features))
                X_seq[0, -len(X):] = X
            else:
                X_seq = np.array(X_seq)
        else:
            X_seq = X

        predictions = self.model.predict(X_seq, verbose=0)
        return predictions.flatten()
