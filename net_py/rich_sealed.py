"""Rich world on the held-out set."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
Xtr, ytr, _ = data.load(str(ROOT / "results/rich-train-windows.csv"))
raw_s, ys, _ = data.read_csv(str(ROOT / "results/sealed-windows.csv"))
Xs = data.encode(raw_s)
print(f"training: {len(ytr)} windows; held-out set: {len(ys)} windows, labelled {int(ys.sum())}\n")
for s in (7, 17, 27):
    net = model.train(Xtr, ytr, [12] * 8, epochs=120, seed=s)
    print(evaluate.fmt(f"rich world, seed {s}", evaluate.summary(model.predict(net, Xs), ys)))
