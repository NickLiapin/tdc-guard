"""Judge over weak learners - on the held-out set."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402
from council import to_ranks, train_judge, judge_predict  # noqa: E402
from weak_council import build_weak, votes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

Xtr, ytr, _ = data.load(str(ROOT / "results/synth-train-windows.csv"))
Xex, yex, _ = data.load(str(ROOT / "results/synth-exam-windows.csv"))
raw_s, ys, _ = data.read_csv(str(ROOT / "results/sealed-windows.csv"))
Xs = data.encode(raw_s)
print(f"held-out set: {len(ys)} windows, labelled {int(ys.sum())}\n")

for ps in (100, 200, 300):
    pool = build_weak(Xtr, ytr, epochs=16, seed0=ps)
    Vex, Vs = votes(pool, Xex), votes(pool, Xs)
    judge = train_judge(Vex, yex)
    r = np.mean([to_ranks(Vs[:, i]) for i in range(Vs.shape[1])], axis=0)
    print(evaluate.fmt(f"weak, ranks (pool {ps})", evaluate.summary(r, ys)))
    print(evaluate.fmt(f"JUDGE (pool {ps})", evaluate.summary(judge_predict(judge, Vs), ys)))
