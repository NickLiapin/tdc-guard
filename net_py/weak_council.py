"""Weak heterogeneous learners and a judge over them.

Observation: the strong networks solve the synthetic data at AUC 1.0000 and agree
with each other (spread 0.0002). The judge has nothing to learn from.

The idea: make the members DELIBERATELY weak and DIFFERENT, so that they err in
different places. Then the judge has a job: to understand whom to trust and when.

Three sources of diversity at once:
  * each network sees only a SUBSET of the features (as in a random forest);
  * each learns on a SUBSET of the training windows;
  * each trains briefly and with small capacity.

The judge is still trained on the synthetic exam and never sees real data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402
from council import to_ranks, train_judge, judge_predict  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def build_weak(Xtr, ytr, n_learners=12, n_feat=8, frac=0.6, hidden=(12, 12),
               epochs=4, seed0=100):
    """Assembles a pool of weak learners; returns (network, feature set)."""
    rng = np.random.default_rng(seed0)
    pool = []
    for i in range(n_learners):
        feats = np.sort(rng.choice(Xtr.shape[1], size=n_feat, replace=False))
        rows = rng.choice(len(ytr), size=int(len(ytr) * frac), replace=False)
        net = model.train(Xtr[np.ix_(rows, feats)], ytr[rows], list(hidden),
                          epochs=epochs, seed=seed0 + i)
        pool.append((net, feats))
    return pool


def votes(pool, X):
    return np.stack([model.predict(net, X[:, feats]) for net, feats in pool], axis=1)


def main() -> None:
    Xtr, ytr, _ = data.load(str(ROOT / "results/synth-train-windows.csv"))
    Xex, yex, _ = data.load(str(ROOT / "results/synth-exam-windows.csv"))
    X8, y8, _ = data.load(str(ROOT / "results/day8-shared.csv"))
    X12, y12, _ = data.load(str(ROOT / "results/day12-frozen-windows.csv"))

    for epochs in (2, 4, 10, 30):
        pool = build_weak(Xtr, ytr, epochs=epochs)
        Vex, V8, V12 = votes(pool, Xex), votes(pool, X8), votes(pool, X12)
        aucs = np.array([evaluate.auc(Vex[:, i], yex) for i in range(Vex.shape[1])])
        spread = float(np.mean(np.std(Vex, axis=1)))

        print(f"\n=== weak learners, {epochs} epochs ===")
        print(f"  their AUC on synthetic data: min {aucs.min():.4f}, median "
              f"{np.median(aucs):.4f}, max {aucs.max():.4f}")
        print(f"  spread of opinions: {spread:.4f}   (the strong networks had 0.0002)")

        ranks8 = np.mean([to_ranks(V8[:, i]) for i in range(V8.shape[1])], axis=0)
        ranks12 = np.mean([to_ranks(V12[:, i]) for i in range(V12.shape[1])], axis=0)
        judge = train_judge(Vex, yex)
        print(f"  day 8:  mean of ranks {evaluate.auc(ranks8, y8):.5f}   "
              f"JUDGE {evaluate.auc(judge_predict(judge, V8), y8):.5f}")
        print(f"  day 12: mean of ranks {evaluate.auc(ranks12, y12):.5f}   "
              f"JUDGE {evaluate.auc(judge_predict(judge, V12), y12):.5f}")


if __name__ == "__main__":
    main()
