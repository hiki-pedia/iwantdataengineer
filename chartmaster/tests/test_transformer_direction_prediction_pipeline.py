from pathlib import PurePosixPath

import pandas as pd

from chartmaster.pipelines.local_transformer_direction_prediction import merge_with_existing_predictions
from chartmaster.storage.local import LocalObjectStorage


def test_market_prediction_merge_keeps_other_market_rows(tmp_path) -> None:
    storage = LocalObjectStorage(tmp_path)
    path = PurePosixPath("reports") / "predictions" / "direction_5d" / "latest.csv"
    existing = pd.DataFrame(
        [
            {"symbol": "AAPL", "market": "US", "positive_probability_5d": 0.6},
            {"symbol": "005930.KS", "market": "KR", "positive_probability_5d": 0.4},
        ]
    )
    replacement = pd.DataFrame(
        [
            {"symbol": "000660.KS", "market": "KR", "positive_probability_5d": 0.7},
        ]
    )
    storage.write_dataframe_csv(existing, path)

    merged = merge_with_existing_predictions(storage, replacement, "KR")

    assert set(merged["symbol"]) == {"AAPL", "000660.KS"}
    assert "005930.KS" not in set(merged["symbol"])
