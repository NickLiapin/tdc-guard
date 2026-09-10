"""Gradient boosting on the held-out set."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import xgboost as xgb
sys.path.insert(0, str(Path(__file__).parent))
import data, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
Xtr, ytr, _ = data.load(str(ROOT / "results/synth-train-windows.csv"))
raw_s, ys, _ = data.read_csv(str(ROOT / "results/sealed-windows.csv"))
Xs = data.encode(raw_s)
print(f"held-out set: {len(ys)} windows, labelled {int(ys.sum())}\n")

pw = (len(ytr) - ytr.sum()) / ytr.sum()
for s in (7, 17, 27):
    clf = xgb.XGBClassifier(max_depth=10, n_estimators=300, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, scale_pos_weight=pw,
                            random_state=s, tree_method="hist", n_jobs=4,
                            eval_metric="logloss")
    clf.fit(Xtr, ytr)
    print(evaluate.fmt(f"boosting, seed {s}", evaluate.summary(clf.predict_proba(Xs)[:, 1], ys)))
