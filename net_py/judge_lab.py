"""Experiment: what to train the judge on so that it is useful.

Observation from the previous run: a judge trained on the easy synthetic exam
LOSES to plain rank averaging. Hypothesis: there all base networks agree and are
almost always right, so the judge learns "trust everyone" - a strategy that is
useless exactly where the opinions diverge.

We check four training grounds for the judge:
  1. the easy synthetic exam (as before);
  2. a HARD synthetic exam - the same sample, but the baseline cut to a quarter,
     which reproduces the early-day regime where the networks make mistakes;
  3. undertrained - the judge learns on the outputs of weakly trained networks;
  4. easy + hard together.

The judge still never sees real data.
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
SEEDS = [7, 17, 27]
MEMBERS = [("deep 32x6", [32] * 6), ("deep 16x8", [16] * 8), ("deep 20x6", [20] * 6)]


def votes(nets, X):
    """Members' votes: a matrix (N, number of members)."""
    return np.stack([model.predict(n, X) for n in nets], axis=1)


def main() -> None:
    Xtr, ytr, _ = data.load(str(ROOT / "results/synth-train-windows.csv"))
    Xse, yse, _ = data.load(str(ROOT / "results/synth-exam-windows.csv"))
    Xhd, yhd, _ = data.load(str(ROOT / "results/synth-exam-hard.csv"))
    X8, y8, _ = data.load(str(ROOT / "results/day8-shared.csv"))
    X12, y12, _ = data.load(str(ROOT / "results/day12-frozen-windows.csv"))

    # members: averaged over seeds within each architecture
    strong, weak = [], []
    for _, hidden in MEMBERS:
        strong.append([model.train(Xtr, ytr, hidden, epochs=120, seed=s) for s in SEEDS])
        weak.append([model.train(Xtr, ytr, hidden, epochs=6, seed=s) for s in SEEDS])

    def avg_votes(groups, X):
        return np.stack([np.mean([model.predict(n, X) for n in g], axis=0) for g in groups], axis=1)

    V_se, V_hd = avg_votes(strong, Xse), avg_votes(strong, Xhd)
    V8, V12 = avg_votes(strong, X8), avg_votes(strong, X12)
    W_se = avg_votes(weak, Xse)
    W8, W12 = avg_votes(weak, X8), avg_votes(weak, X12)

    print("=== how much the members err on each training ground ===")
    for tag, V, y in (("easy synth.", V_se, yse), ("HARD synth.", V_hd, yhd),
                      ("undertrained, easy", W_se, yse)):
        aucs = [evaluate.auc(V[:, i], y) for i in range(V.shape[1])]
        spread = float(np.mean(np.std(V, axis=1)))
        print(f"  {tag:<18} member AUCs {['%.4f' % a for a in aucs]}  "
              f"mean spread of opinions {spread:.4f}")

    print("\n=== reference ways of combining ===")
    for tag, V, y in (("day 8", V8, y8), ("day 12", V12, y12)):
        r = np.mean([to_ranks(V[:, i]) for i in range(V.shape[1])], axis=0)
        print(f"  {tag}: mean of ranks AUC {evaluate.auc(r, y):.5f}")

    print("\n=== judge trained on different grounds ===")
    trials = [
        ("easy synth.", V_se, yse, V8, V12),
        ("HARD synth.", V_hd, yhd, V8, V12),
        ("undertrained", W_se, yse, W8, W12),
        ("easy + hard", np.vstack([V_se, V_hd]), np.concatenate([yse, yhd]), V8, V12),
    ]
    for name, P, y, P8, P12 in trials:
        j = train_judge(P, y)
        a8 = evaluate.auc(judge_predict(j, P8), y8)
        a12 = evaluate.auc(judge_predict(j, P12), y12)
        print(f"  {name:<20} day 8 {a8:.5f}   day 12 {a12:.5f}")


if __name__ == "__main__":
    main()
