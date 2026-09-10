"""Robustness check: a judge over weak learners, several independent pools.
A single measurement has already misled us twice, so every setting is repeated
on different sets of learners.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402
from council import to_ranks, train_judge, judge_predict  # noqa: E402
from weak_council import build_weak, votes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POOL_SEEDS = [100, 200, 300, 400, 500]

Xtr, ytr, _ = data.load(str(ROOT / "results/synth-train-windows.csv"))
Xex, yex, _ = data.load(str(ROOT / "results/synth-exam-windows.csv"))
X8, y8, _ = data.load(str(ROOT / "results/day8-shared.csv"))
X12, y12, _ = data.load(str(ROOT / "results/day12-frozen-windows.csv"))

print(f"{'epochs':>5}{'spread':>10}{'d8 ranks':>12}{'d8 judge':>12}"
      f"{'d12 ranks':>16}{'d12 judge':>18}")
print("-" * 74)

for epochs in (6, 8, 10, 12, 16):
    r8, j8, r12, j12, spreads = [], [], [], [], []
    for ps in POOL_SEEDS:
        pool = build_weak(Xtr, ytr, epochs=epochs, seed0=ps)
        Vex, V8, V12 = votes(pool, Xex), votes(pool, X8), votes(pool, X12)
        spreads.append(float(np.mean(np.std(Vex, axis=1))))
        judge = train_judge(Vex, yex)
        r8.append(evaluate.auc(np.mean([to_ranks(V8[:, i]) for i in range(V8.shape[1])], axis=0), y8))
        j8.append(evaluate.auc(judge_predict(judge, V8), y8))
        r12.append(evaluate.auc(np.mean([to_ranks(V12[:, i]) for i in range(V12.shape[1])], axis=0), y12))
        j12.append(evaluate.auc(judge_predict(judge, V12), y12))
    f = lambda a: f"{np.mean(a):.5f}+-{np.std(a):.5f}"
    print(f"{epochs:>5}{np.mean(spreads):>10.4f}{f(r8):>16}{f(j8):>14}{f(r12):>18}{f(j12):>18}")
