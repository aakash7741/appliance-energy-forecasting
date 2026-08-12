from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def chronos_rolling(
    series: pd.Series,
    train_end: int,
    horizon: int = 24,
    model_id: str = "amazon/chronos-t5-tiny",
    samples: int = 40,
):
    """Run the public Chronos-T5 checkpoint zero-shot; return status explicitly."""
    try:
        # Optional heavyweight dependencies live outside the analysis environment.
        dependency_dir = Path(__file__).resolve().parents[2] / ".python_packages"
        if dependency_dir.exists() and str(dependency_dir) not in sys.path:
            sys.path.append(str(dependency_dir))
        import torch
        from chronos import ChronosPipeline

        torch.manual_seed(42)
        pipeline = ChronosPipeline.from_pretrained(model_id, device_map="cpu", torch_dtype=torch.float32)
        medians, lowers, uppers = [], [], []
        for origin in range(train_end, len(series), horizon):
            steps = min(horizon, len(series) - origin)
            context = torch.tensor(series.iloc[max(0, origin - 512) : origin].to_numpy(), dtype=torch.float32)
            draws = pipeline.predict(context, prediction_length=steps, num_samples=samples)[0]
            medians.extend(torch.quantile(draws, 0.5, dim=0).numpy())
            lowers.extend(torch.quantile(draws, 0.05, dim=0).numpy())
            uppers.extend(torch.quantile(draws, 0.95, dim=0).numpy())
        index = series.index[train_end:]
        frame = pd.DataFrame(
            {
                "forecast": np.maximum(medians, 0),
                "lower_90": np.maximum(lowers, 0),
                "upper_90": np.maximum(uppers, 0),
            },
            index=index,
        )
        return frame, {"status": "succeeded", "model": model_id, "samples": samples, "context_length": 512}
    except Exception as exc:
        return None, {"status": "unavailable", "model": model_id, "error": f"{type(exc).__name__}: {exc}"}
