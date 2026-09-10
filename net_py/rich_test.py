"""Rich world: did it become harder, and what did that give on real data."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEDS = [7, 17, 27]
HIDDEN = [12] * 8

X8, y8, _ = data.load(str(ROOT / "results/day8-shared.csv"))
X12, y12, _ = data.load(str(ROOT / "results/day12-frozen-windows.csv"))

for world, tr, ex in (("previous", "synth-train-windows", "synth-exam-windows"),
                      ("RICH", "rich-train-windows", "rich-exam-windows")):
    Xtr, ytr, _ = data.load(str(ROOT / f"results/{tr}.csv"))
    Xex, yex, _ = data.load(str(ROOT / f"results/{ex}.csv"))
    a_syn, a8, a12 = [], [], []
    for s in SEEDS:
        net = model.train(Xtr, ytr, HIDDEN, epochs=120, seed=s)
        a_syn.append(evaluate.auc(model.predict(net, Xex), yex))
        a8.append(evaluate.auc(model.predict(net, X8), y8))
        a12.append(evaluate.auc(model.predict(net, X12), y12))
    f = lambda a: f"{np.mean(a):.5f}+-{np.std(a):.5f}"
    print(f"\n=== world: {world} ({len(ytr)} windows, labelled {int(ytr.sum())}) ===")
    print(f"  own synthetic:  {f(a_syn)}   <- is it no longer solved to 1.0")
    print(f"  day 8:          {f(a8)}")
    print(f"  day 12:         {f(a12)}")
