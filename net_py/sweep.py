"""Sweep over the network's capacity and depth.

The architecture is chosen ONLY on the working days (8 and 12). The held-out set
takes no part in the choice - otherwise it stops being an honest measure.

Every architecture is trained on several seeds: the difference between two
networks may turn out to be ordinary initialisation noise, and without repeats
it cannot be told from a real effect.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEDS = [7, 17, 27]

ARCHS = [
    ("flat, tiny",              [8]),
    ("flat, small",             [16]),
    ("flat, medium",            [32]),
    ("flat, large",             [64]),
    ("flat, up to 2000",        [100]),
    ("two steps (base)",        [24, 12]),
    ("two steps, wider",        [32, 16]),
    ("two steps, wider still",  [48, 24]),
    ("narrow and deep x3",      [16, 16, 16]),
    ("narrow and deep x5",      [16, 16, 16, 16, 16]),
    ("narrow and deep x8",      [12] * 8),
    ("wide input, narrowing",   [100, 50, 25]),
]


def main() -> None:
    X, y, _ = data.load(str(ROOT / "results/synth-train-windows.csv"))
    reals = [
        ("day 8", *data.load(str(ROOT / "results/day8-shared.csv"))[:2]),
        ("day 12", *data.load(str(ROOT / "results/day12-frozen-windows.csv"))[:2]),
    ]

    print(f"{'architecture':<26}{'weights':>7}  "
          f"{'day 8: AUC':>13}{'false alarms':>9}  {'day 12: AUC':>14}{'false alarms':>9}")
    print("-" * 84)

    results = []
    for name, hidden in ARCHS:
        per_seed = {"d8_auc": [], "d8_fp": [], "d12_auc": [], "d12_fp": []}
        n_params = 0
        for seed in SEEDS:
            net = model.train(X, y, hidden, epochs=120, seed=seed)
            n_params = net.n_params
            for tag, (_, Xr, yr) in zip(["d8", "d12"], [("", *reals[0][1:]), ("", *reals[1][1:])]):
                s = evaluate.summary(model.predict(net, Xr), yr)
                per_seed[f"{tag}_auc"].append(s["auc"])
                # the price of half the catch - more stable than "before all"
                per_seed[f"{tag}_fp"].append(s["fp_at_50"])
        row = {k: (float(np.mean(v)), float(np.std(v))) for k, v in per_seed.items()}
        results.append((name, hidden, n_params, row))
        print(f"{name:<26}{n_params:>7}  "
              f"{row['d8_auc'][0]:>8.5f}+-{row['d8_auc'][1]:.5f}{row['d8_fp'][0]:>9.0f}  "
              f"{row['d12_auc'][0]:>9.5f}+-{row['d12_auc'][1]:.5f}{row['d12_fp'][0]:>9.0f}")

    print("\nBest by mean AUC over the working days:")
    ranked = sorted(results, key=lambda r: -(r[3]["d8_auc"][0] + r[3]["d12_auc"][0]) / 2)
    for name, hidden, n, row in ranked[:4]:
        avg = (row["d8_auc"][0] + row["d12_auc"][0]) / 2
        print(f"  {name:<26} {str(hidden):<22} {n:>6} weights   mean AUC {avg:.5f}")


if __name__ == "__main__":
    main()
