"""Final run of the chosen architecture on the held-out set.

The architecture was chosen on the working days (see sweep.py); the held-out set
took no part in the choice. Comparison with the reference solutions - on the very same windows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HIDDEN = [12] * 8
SEEDS = [7, 17, 27]

X, y, _ = data.load(str(ROOT / "results/synth-train-windows.csv"))
raw_s, ys, _ = data.read_csv(str(ROOT / "results/sealed-windows.csv"))
Xs = data.encode(raw_s)
print(f"held-out set: {len(ys)} windows, labelled {int(ys.sum())}\n")

for seed in SEEDS:
    net = model.train(X, y, HIDDEN, epochs=120, seed=seed)
    s = evaluate.summary(model.predict(net, Xs), ys)
    print(evaluate.fmt(f"deep x8, seed {seed}", s))

# reference solutions on the same windows: columns in original units
col = {name: i for i, name in enumerate(data.FEATURES)}
print()
print(evaluate.fmt("counter: accounts", evaluate.summary(raw_s[:, col["users"]], ys)))
print(evaluate.fmt("counter: destinations", evaluate.summary(raw_s[:, col["dsts"]], ys)))
