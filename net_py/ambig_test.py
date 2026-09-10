"""Check: does irreducible ambiguity in the world give anything useful.

Hypothesis: the base networks solve the synthetic data at AUC 1.0000, there is
nothing to argue about, and so the judge is useless. If the world gets windows
that CANNOT be told apart by construction (an administrator on their rounds looks
like an intruder), the synthetic data stops being perfectly separable - and there
is something to arbitrate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402
from council import to_ranks, train_judge, judge_predict  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEDS = [7, 17, 27]
MEMBERS = [[32] * 6, [16] * 8, [20] * 6]

X8, y8, _ = data.load(str(ROOT / "results/day8-shared.csv"))
X12, y12, _ = data.load(str(ROOT / "results/day12-frozen-windows.csv"))

for world, tr, ex in (("base", "synth-train-windows", "synth-exam-windows"),
                      ("with admin", "amb-train-windows", "amb-exam-windows")):
    Xtr, ytr, _ = data.load(str(ROOT / f"results/{tr}.csv"))
    Xex, yex, _ = data.load(str(ROOT / f"results/{ex}.csv"))
    groups = [[model.train(Xtr, ytr, h, epochs=120, seed=s) for s in SEEDS] for h in MEMBERS]
    avg = lambda g, X: np.mean([model.predict(n, X) for n in g], axis=0)

    Vex = np.stack([avg(g, Xex) for g in groups], axis=1)
    V8 = np.stack([avg(g, X8) for g in groups], axis=1)
    V12 = np.stack([avg(g, X12) for g in groups], axis=1)

    aucs = [evaluate.auc(Vex[:, i], yex) for i in range(Vex.shape[1])]
    print(f"\n=== world: {world} ===")
    print(f"  on its own synthetic data: member AUCs {['%.5f' % a for a in aucs]}")
    print(f"  spread of opinions on synthetic data: {float(np.mean(np.std(Vex, axis=1))):.5f}")

    for tag, V, y in (("day 8", V8, y8), ("day 12", V12, y12)):
        r = np.mean([to_ranks(V[:, i]) for i in range(V.shape[1])], axis=0)
        print(f"  {tag}: best single {max(evaluate.auc(V[:, i], y) for i in range(V.shape[1])):.5f}"
              f"   council(ranks) {evaluate.auc(r, y):.5f}", end="")
        j = train_judge(Vex, yex)
        print(f"   judge {evaluate.auc(judge_predict(j, V), y):.5f}")
