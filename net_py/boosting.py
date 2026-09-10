"""Gradient boosting on the same features.

A gap in our experiments: for tabular data, tree boosting is the standard and
often beats neural networks. We never checked it.

Same conditions: training ONLY on synthetic data, evaluation on real journals.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import xgboost as xgb

sys.stdout.reconfigure(line_buffering=True)  # lines show up immediately, even if the process dies

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEDS = [7, 17, 27]

Xtr, ytr, _ = data.load(str(ROOT / "results/synth-train-windows.csv"))
Xex, yex, _ = data.load(str(ROOT / "results/synth-exam-windows.csv"))
X8, y8, _ = data.load(str(ROOT / "results/day8-shared.csv"))
X12, y12, _ = data.load(str(ROOT / "results/day12-frozen-windows.csv"))

pos_weight = (len(ytr) - ytr.sum()) / ytr.sum()

CONFIGS = [
    ("depth 3, 200 trees", dict(max_depth=3, n_estimators=200, learning_rate=0.1)),
    ("depth 6, 300 trees", dict(max_depth=6, n_estimators=300, learning_rate=0.1)),
    ("depth 10, 300 trees", dict(max_depth=10, n_estimators=300, learning_rate=0.05)),
    ("depth 2, 800 trees", dict(max_depth=2, n_estimators=800, learning_rate=0.05)),
    # with subsampling: only then does boosting depend on the seed,
    # and only then is the spread estimate honest
    ("depth 10 + subsample 0.8", dict(max_depth=10, n_estimators=300,
        learning_rate=0.05, subsample=0.8, colsample_bytree=0.8)),
    ("depth 14 + subsample 0.8", dict(max_depth=14, n_estimators=400,
        learning_rate=0.05, subsample=0.8, colsample_bytree=0.8)),
]

print(f"{'model':<28}{'synthetic':>12}{'day 8':>18}{'day 12':>20}")
print("-" * 78)

for name, params in CONFIGS:
    a_syn, a8, a12 = [], [], []
    for s in SEEDS:
        clf = xgb.XGBClassifier(
            **params, scale_pos_weight=pos_weight, random_state=s,
            tree_method="hist", n_jobs=4, eval_metric="logloss",
        )
        clf.fit(Xtr, ytr)
        a_syn.append(evaluate.auc(clf.predict_proba(Xex)[:, 1], yex))
        a8.append(evaluate.auc(clf.predict_proba(X8)[:, 1], y8))
        a12.append(evaluate.auc(clf.predict_proba(X12)[:, 1], y12))
    f = lambda a: f"{np.mean(a):.5f}+-{np.std(a):.5f}"
    print(f"{name:<28}{np.mean(a_syn):>12.5f}{f(a8):>18}{f(a12):>20}")

# The reference point is our network. Not computed by default: on macOS torch
# and xgboost each pull in their own libomp, and training the network after
# boosting in one process crashes python with code 139. The same row is printed
# by net_py/run.py with --hidden 12,12,12,12,12,12,12,12; if you want it in one
# table - run with the --with-net flag at your own risk.
if "--with-net" in sys.argv:
    a8, a12 = [], []
    for s in SEEDS:
        net = model.train(Xtr, ytr, [12] * 8, epochs=120, seed=s)
        a8.append(evaluate.auc(model.predict(net, X8), y8))
        a12.append(evaluate.auc(model.predict(net, X12), y12))
    f = lambda a: f"{np.mean(a):.5f}+-{np.std(a):.5f}"
    print(f"{'NETWORK [12]x8 (ours)':<28}{'-':>12}{f(a8):>18}{f(a12):>20}")
else:
    print("\nreference network row: python3 net_py/run.py --hidden 12,12,12,12,12,12,12,12 (or this script with --with-net)")
