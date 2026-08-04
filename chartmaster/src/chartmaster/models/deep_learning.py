"""Deep learning experiment contracts."""

import pandas as pd


def build_sequence_dataset(features: pd.DataFrame, window_size: int = 60) -> object:
    """Build rolling-window tensors for LSTM/Transformer experiments."""
    raise NotImplementedError("Add after the baseline ML pipeline is stable.")


def train_sequence_model(sequence_dataset: object) -> object:
    """Train an LSTM/Transformer-style sequence model."""
    raise NotImplementedError("Choose PyTorch or TensorFlow before implementing this.")

