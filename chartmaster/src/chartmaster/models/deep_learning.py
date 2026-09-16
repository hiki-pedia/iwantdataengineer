"""PyTorch sequence models for chart direction experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from chartmaster.models.direction import FEATURE_COLUMNS, TARGET_COLUMN


@dataclass(frozen=True)
class SequenceDataset:
    features: np.ndarray
    targets: np.ndarray
    dates: list[str]
    symbols: list[str]


@dataclass(frozen=True)
class SequenceInferenceDataset:
    features: np.ndarray
    dates: list[str]
    symbols: list[str]


class LstmDirectionClassifier(nn.Module):
    """Small LSTM classifier for 5-trading-day direction."""

    def __init__(self, input_size: int, hidden_size: int = 32, dropout: float = 0.1) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, num_layers=1, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_size, 1)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        output, _ = self.lstm(inputs)
        last_hidden = output[:, -1, :]
        return self.classifier(self.dropout(last_hidden)).squeeze(-1)


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding for lightweight Transformer experiments."""

    def __init__(self, model_size: int, max_length: int = 512) -> None:
        super().__init__()
        position = torch.arange(max_length).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, model_size, 2) * (-np.log(10000.0) / model_size))
        encoding = torch.zeros(max_length, model_size)
        encoding[:, 0::2] = torch.sin(position * div_term)
        encoding[:, 1::2] = torch.cos(position * div_term[: encoding[:, 1::2].shape[1]])
        self.register_buffer("encoding", encoding.unsqueeze(0))

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return inputs + self.encoding[:, : inputs.size(1), :]


class TransformerDirectionClassifier(nn.Module):
    """Small Transformer encoder classifier for chart sequence direction."""

    def __init__(
        self,
        input_size: int,
        model_size: int = 32,
        num_heads: int = 4,
        num_layers: int = 1,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input_projection = nn.Linear(input_size, model_size)
        self.position = PositionalEncoding(model_size)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=model_size,
            nhead=num_heads,
            dim_feedforward=model_size * 4,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(model_size, 1)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        encoded = self.encoder(self.position(self.input_projection(inputs)))
        pooled = encoded[:, -1, :]
        return self.classifier(self.dropout(pooled)).squeeze(-1)


def prepare_sequence_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize a dataframe before sequence generation."""
    required_columns = ["date", "symbol", *FEATURE_COLUMNS, TARGET_COLUMN]
    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing sequence columns: {', '.join(missing)}")
    output = dataframe[required_columns].copy()
    output["date"] = pd.to_datetime(output["date"])
    output = output.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN])
    output[TARGET_COLUMN] = output[TARGET_COLUMN].astype(bool)
    return output.sort_values(["symbol", "date"]).reset_index(drop=True)


def fit_scaler(training_frame: pd.DataFrame) -> StandardScaler:
    scaler = StandardScaler()
    scaler.fit(training_frame[FEATURE_COLUMNS])
    return scaler


def build_sequence_dataset(dataframe: pd.DataFrame, scaler: StandardScaler, window_size: int = 60) -> SequenceDataset:
    """Build rolling-window tensors for LSTM experiments."""
    if window_size < 2:
        raise ValueError("window_size must be at least 2")

    frame = prepare_sequence_frame(dataframe)
    sequences: list[np.ndarray] = []
    targets: list[bool] = []
    dates: list[str] = []
    symbols: list[str] = []
    for symbol, group in frame.groupby("symbol", sort=False):
        group = group.sort_values("date").reset_index(drop=True)
        scaled = scaler.transform(group[FEATURE_COLUMNS])
        target = group[TARGET_COLUMN].to_numpy(dtype=bool)
        date_values = group["date"].dt.date.astype(str).tolist()
        for end_index in range(window_size - 1, len(group)):
            start_index = end_index - window_size + 1
            sequences.append(scaled[start_index : end_index + 1])
            targets.append(bool(target[end_index]))
            dates.append(date_values[end_index])
            symbols.append(str(symbol))

    if not sequences:
        return SequenceDataset(
            features=np.empty((0, window_size, len(FEATURE_COLUMNS)), dtype=np.float32),
            targets=np.empty((0,), dtype=np.float32),
            dates=[],
            symbols=[],
        )
    return SequenceDataset(
        features=np.asarray(sequences, dtype=np.float32),
        targets=np.asarray(targets, dtype=np.float32),
        dates=dates,
        symbols=symbols,
    )


def build_latest_sequence_dataset(dataframe: pd.DataFrame, scaler: StandardScaler, window_size: int = 60) -> SequenceInferenceDataset:
    """Build one latest rolling-window tensor per symbol for inference."""
    if window_size < 2:
        raise ValueError("window_size must be at least 2")
    required_columns = ["date", "symbol", *FEATURE_COLUMNS]
    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing inference columns: {', '.join(missing)}")

    frame = dataframe[required_columns].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.dropna(subset=FEATURE_COLUMNS)
    frame = frame.sort_values(["symbol", "date"]).reset_index(drop=True)

    sequences: list[np.ndarray] = []
    dates: list[str] = []
    symbols: list[str] = []
    for symbol, group in frame.groupby("symbol", sort=False):
        group = group.sort_values("date").reset_index(drop=True)
        if len(group) < window_size:
            continue
        scaled = scaler.transform(group[FEATURE_COLUMNS])
        sequences.append(scaled[-window_size:])
        dates.append(str(group["date"].dt.date.iloc[-1]))
        symbols.append(str(symbol))

    if not sequences:
        return SequenceInferenceDataset(
            features=np.empty((0, window_size, len(FEATURE_COLUMNS)), dtype=np.float32),
            dates=[],
            symbols=[],
        )
    return SequenceInferenceDataset(
        features=np.asarray(sequences, dtype=np.float32),
        dates=dates,
        symbols=symbols,
    )


def train_lstm_direction(
    training_dataset: SequenceDataset,
    validation_dataset: SequenceDataset,
    *,
    hidden_size: int = 32,
    epochs: int = 8,
    batch_size: int = 256,
    learning_rate: float = 0.001,
    random_state: int = 42,
) -> tuple[LstmDirectionClassifier, dict[str, object]]:
    """Train a compact LSTM direction model on CPU."""
    if len(training_dataset.targets) == 0:
        raise ValueError("training dataset is empty")
    torch.manual_seed(random_state)
    model = LstmDirectionClassifier(input_size=training_dataset.features.shape[-1], hidden_size=hidden_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    positive_count = float(training_dataset.targets.sum())
    negative_count = float(len(training_dataset.targets) - positive_count)
    pos_weight = torch.tensor([negative_count / positive_count if positive_count else 1.0], dtype=torch.float32)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(training_dataset.features), torch.from_numpy(training_dataset.targets)),
        batch_size=batch_size,
        shuffle=False,
    )

    history: list[dict[str, float]] = []
    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for batch_features, batch_targets in train_loader:
            optimizer.zero_grad()
            logits = model(batch_features)
            loss = criterion(logits, batch_targets)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.item()))

        validation_metrics = evaluate_lstm_direction(model, validation_dataset)
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": float(np.mean(losses)) if losses else 0.0,
                "validation_f1": validation_metrics["f1"],
                "validation_roc_auc": validation_metrics.get("roc_auc", 0.0),
            }
        )

    return model, {"epochs": epochs, "history": history}


def train_transformer_direction(
    training_dataset: SequenceDataset,
    validation_dataset: SequenceDataset,
    *,
    model_size: int = 32,
    num_heads: int = 4,
    num_layers: int = 1,
    epochs: int = 3,
    batch_size: int = 512,
    learning_rate: float = 0.001,
    random_state: int = 42,
) -> tuple[TransformerDirectionClassifier, dict[str, object]]:
    """Train a compact Transformer encoder direction model on CPU."""
    if len(training_dataset.targets) == 0:
        raise ValueError("training dataset is empty")
    torch.manual_seed(random_state)
    model = TransformerDirectionClassifier(
        input_size=training_dataset.features.shape[-1],
        model_size=model_size,
        num_heads=num_heads,
        num_layers=num_layers,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    positive_count = float(training_dataset.targets.sum())
    negative_count = float(len(training_dataset.targets) - positive_count)
    pos_weight = torch.tensor([negative_count / positive_count if positive_count else 1.0], dtype=torch.float32)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(training_dataset.features), torch.from_numpy(training_dataset.targets)),
        batch_size=batch_size,
        shuffle=False,
    )

    history: list[dict[str, float]] = []
    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for batch_features, batch_targets in train_loader:
            optimizer.zero_grad()
            logits = model(batch_features)
            loss = criterion(logits, batch_targets)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.item()))

        validation_metrics = evaluate_lstm_direction(model, validation_dataset)
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": float(np.mean(losses)) if losses else 0.0,
                "validation_f1": validation_metrics["f1"],
                "validation_roc_auc": validation_metrics.get("roc_auc", 0.0),
            }
        )

    return model, {"epochs": epochs, "history": history}


def predict_lstm_probabilities(model: nn.Module, dataset: SequenceDataset) -> np.ndarray:
    if len(dataset.targets) == 0:
        return np.empty((0,), dtype=np.float32)
    model.eval()
    with torch.no_grad():
        logits = model(torch.from_numpy(dataset.features))
        return torch.sigmoid(logits).numpy()


def predict_sequence_probabilities(model: nn.Module, features: np.ndarray) -> np.ndarray:
    """Return positive-class probabilities for sequence tensors."""
    if len(features) == 0:
        return np.empty((0,), dtype=np.float32)
    model.eval()
    with torch.no_grad():
        logits = model(torch.from_numpy(features))
        return torch.sigmoid(logits).numpy()


def latest_sequence_prediction_frame(
    model: nn.Module,
    dataset: SequenceInferenceDataset,
    probability_column: str,
) -> pd.DataFrame:
    """Return latest per-symbol inference probabilities."""
    return pd.DataFrame(
        {
            "symbol": dataset.symbols,
            "as_of_date": dataset.dates,
            probability_column: predict_sequence_probabilities(model, dataset.features),
        }
    )


def sequence_prediction_frame(model: nn.Module, dataset: SequenceDataset, probability_column: str) -> pd.DataFrame:
    """Return sequence model probabilities with symbol/date keys."""
    return pd.DataFrame(
        {
            "symbol": dataset.symbols,
            "date": dataset.dates,
            TARGET_COLUMN: dataset.targets.astype(bool),
            probability_column: predict_lstm_probabilities(model, dataset),
        }
    )


def evaluate_lstm_direction(
    model: nn.Module,
    dataset: SequenceDataset,
    *,
    threshold: float = 0.5,
) -> dict[str, float]:
    """Evaluate an LSTM classifier with the same metrics as tabular models."""
    if len(dataset.targets) == 0:
        raise ValueError("evaluation dataset is empty")
    y_true = pd.Series(dataset.targets.astype(bool))
    y_score = pd.Series(predict_lstm_probabilities(model, dataset))
    y_pred = y_score >= threshold
    metrics = {
        "row_count": float(len(y_true)),
        "positive_ratio": float(y_true.mean()),
        "predicted_positive_ratio": float(y_pred.mean()),
        "threshold": float(threshold),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    if y_true.nunique() > 1:
        metrics["roc_auc"] = roc_auc_score(y_true, y_score)
    return {key: float(value) for key, value in metrics.items()}


def find_best_lstm_threshold(
    model: nn.Module,
    validation_dataset: SequenceDataset,
    minimum_threshold: float = 0.1,
    maximum_threshold: float = 0.9,
    step: float = 0.01,
) -> tuple[float, dict[str, float]]:
    """Find the validation F1 threshold for an LSTM model."""
    y_true = pd.Series(validation_dataset.targets.astype(bool))
    y_score = pd.Series(predict_lstm_probabilities(model, validation_dataset))
    candidates = []
    threshold = minimum_threshold
    while threshold <= maximum_threshold + 1e-9:
        y_pred = y_score >= round(threshold, 4)
        metrics = {
            "row_count": float(len(y_true)),
            "positive_ratio": float(y_true.mean()),
            "predicted_positive_ratio": float(y_pred.mean()),
            "threshold": float(round(threshold, 4)),
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        }
        if y_true.nunique() > 1:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_score))
        candidates.append((metrics["f1"], metrics["precision"], -abs(metrics["threshold"] - 0.5), metrics))
        threshold += step
    best = max(candidates, key=lambda item: item[:3])[3]
    return best["threshold"], best
