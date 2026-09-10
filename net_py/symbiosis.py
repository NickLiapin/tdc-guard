"""Symbiosis: a judge over a MIXED pool.

A direct substitution - train the judge on the weak and feed it the strong - is
no good: the judge would see at its input a distribution of votes that was
absent in training. The right version: the pool is heterogeneous from the start,
and the judge learns on that very pool.

  * weak learners give the judge a dispute - something to arbitrate;
  * strong ones give precision where there is nothing to argue about.

Every setting is repeated on several pools: single measurements in this project
have already twice shown a record that was not confirmed afterwards.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402
from council import to_ranks, train_judge, judge_predict  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POOLS = [100, 200, 300, 400]
STRONG_ARCHS = [[32] * 6, [16] * 8, [20] * 6, [12] * 8, [12] * 10, [64, 32]]


def build_mixed(Xtr, ytr, seed0, n_weak=6, n_feat=8, frac=0.6, weak_epochs=16):
    """A pool of weak learners (a subset of features, a subset of windows, few epochs) and strong ones."""
    rng = np.random.default_rng(seed0)
    pool = []
    for i in range(n_weak):
        feats = np.sort(rng.choice(Xtr.shape[1], size=n_feat, replace=False))
        rows = rng.choice(len(ytr), size=int(len(ytr) * frac), replace=False)
        net = model.train(Xtr[np.ix_(rows, feats)], ytr[rows], [12, 12],
                          epochs=weak_epochs, seed=seed0 + i)
        pool.append((net, feats))
    all_feats = np.arange(Xtr.shape[1])
    for i, hidden in enumerate(STRONG_ARCHS):
        net = model.train(Xtr, ytr, hidden, epochs=120, seed=seed0 + 50 + i)
        pool.append((net, all_feats))
    return pool


def votes(pool, X):
    return np.stack([model.predict(net, X[:, f]) for net, f in pool], axis=1)


def main() -> None:
    Xtr, ytr, _ = data.load(str(ROOT / "results/synth-train-windows.csv"))
    Xex, yex, _ = data.load(str(ROOT / "results/synth-exam-windows.csv"))
    X8, y8, _ = data.load(str(ROOT / "results/day8-shared.csv"))
    X12, y12, _ = data.load(str(ROOT / "results/day12-frozen-windows.csv"))

    res = {k: [] for k in ("ranks8", "judge8", "ranks12", "judge12", "best12")}
    for ps in POOLS:
        pool = build_mixed(Xtr, ytr, ps)
        Vex, V8, V12 = votes(pool, Xex), votes(pool, X8), votes(pool, X12)
        judge = train_judge(Vex, yex)
        rank = lambda V: np.mean([to_ranks(V[:, i]) for i in range(V.shape[1])], axis=0)
        res["ranks8"].append(evaluate.auc(rank(V8), y8))
        res["judge8"].append(evaluate.auc(judge_predict(judge, V8), y8))
        res["ranks12"].append(evaluate.auc(rank(V12), y12))
        res["judge12"].append(evaluate.auc(judge_predict(judge, V12), y12))
        # the best single strong member in this pool - the reference point
        strong_aucs = [evaluate.auc(V12[:, i], y12) for i in range(6, V12.shape[1])]
        res["best12"].append(max(strong_aucs))

    print("mixed pool: 6 weak + 6 strong, 4 independent pools\n")
    for k, v in res.items():
        print(f"  {k:<12} {np.mean(v):.5f} +- {np.std(v):.5f}")

    print("\nfor comparison (measured earlier):")
    print("  single strong, day 12           0.98183")
    print("  council of strong (ranks)       0.98053")
    print("  judge over weak, day 12         0.97347 +- 0.01876")


if __name__ == "__main__":
    main()
