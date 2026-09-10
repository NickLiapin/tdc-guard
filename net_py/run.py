"""Training on synthetic data and checking on real journals.

    python3 net_py/run.py --hidden 24,12

Real data is used ONLY for checking: not a single line of a live journal
takes part in training.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

TRAIN = "results/synth-train-windows.csv"
SYNTH_EXAM = "results/synth-exam-windows.csv"
REAL = [
    ("day 8 (working)", "results/day8-shared.csv"),
    ("day 12 (working)", "results/day12-frozen-windows.csv"),
]
SEALED = ("held-out set", "results/sealed-windows.csv")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hidden", default="24,12", help="hidden layer widths, comma-separated")
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--sealed", action="store_true", help="run the held-out set")
    args = ap.parse_args()

    hidden = [int(h) for h in args.hidden.split(",") if h]

    X, y, _ = data.load(str(ROOT / TRAIN))
    net = model.train(X, y, hidden, epochs=args.epochs, seed=args.seed)
    print(f"architecture 18-{'-'.join(map(str, hidden))}-1 - {net.n_params} weights")
    print(f"training windows {len(y)}, labelled {int(y.sum())}\n")

    Xe, ye, _ = data.load(str(ROOT / SYNTH_EXAM))
    print(evaluate.fmt("synthetic, other seed", evaluate.summary(model.predict(net, Xe), ye)))

    for name, path in REAL:
        Xr, yr, _ = data.load(str(ROOT / path))
        print(evaluate.fmt(name, evaluate.summary(model.predict(net, Xr), yr)))

    if args.sealed:
        name, path = SEALED
        Xs, ys, _ = data.load(str(ROOT / path))
        print(evaluate.fmt(name, evaluate.summary(model.predict(net, Xs), ys)))


if __name__ == "__main__":
    main()
