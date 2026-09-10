"""Big sweep over architectures + council + judge on top of it.

The same fairness rules:
  * all networks are trained ONLY on synthetic data;
  * the judge (meta-model) learns on the outputs of the base networks computed
    on a SYNTHETIC exam with another seed - it never sees real data either;
  * the choice of architectures and of the council's membership - only on the working days.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEDS = [7, 17, 27]

ARCHS: list[tuple[str, list[int]]] = [
    # flat: grow the width
    ("flat 4", [4]), ("flat 8", [8]), ("flat 16", [16]),
    ("flat 32", [32]), ("flat 64", [64]), ("flat 128", [128]),
    ("flat 256", [256]),
    # two steps
    ("2-layer 16-8", [16, 8]), ("2-layer 24-12", [24, 12]), ("2-layer 32-16", [32, 16]),
    ("2-layer 48-24", [48, 24]), ("2-layer 64-32", [64, 32]), ("2-layer 128-64", [128, 64]),
    # three steps
    ("3-layer 16", [16] * 3), ("3-layer 24", [24] * 3), ("3-layer 32", [32] * 3),
    ("3-layer 64-32-16", [64, 32, 16]),
    # narrow and deep: grow the depth
    ("deep 12x4", [12] * 4), ("deep 12x6", [12] * 6), ("deep 12x8", [12] * 8),
    ("deep 12x10", [12] * 10), ("deep 12x12", [12] * 12),
    ("deep 8x8", [8] * 8), ("deep 16x8", [16] * 8), ("deep 24x8", [24] * 8),
    ("deep 20x6", [20] * 6), ("deep 32x6", [32] * 6),
    # bottleneck in the middle
    ("bottleneck 32-8-32", [32, 8, 32]), ("bottleneck 64-8-64", [64, 8, 64]),
    # pyramid
    ("pyramid 100-50-25", [100, 50, 25]), ("pyramid 64-48-32-16", [64, 48, 32, 16]),
]


def main() -> None:
    t0 = time.time()
    Xtr, ytr, _ = data.load(str(ROOT / "results/synth-train-windows.csv"))
    Xse, yse, _ = data.load(str(ROOT / "results/synth-exam-windows.csv"))
    X8, y8, _ = data.load(str(ROOT / "results/day8-shared.csv"))
    X12, y12, _ = data.load(str(ROOT / "results/day12-frozen-windows.csv"))
    print(f"data loaded in {time.time()-t0:.0f} s\n")

    rows = []
    store: dict[str, dict] = {}   # predictions for the council

    print(f"{'architecture':<22}{'weights':>7}{'d8 AUC':>12}{'d12 AUC':>16}")
    print("-" * 60)
    for name, hidden in ARCHS:
        p_se, p8, p12, aucs8, aucs12, n_params = [], [], [], [], [], 0
        for seed in SEEDS:
            net = model.train(Xtr, ytr, hidden, epochs=120, seed=seed)
            n_params = net.n_params
            a_se = model.predict(net, Xse)
            a8 = model.predict(net, X8)
            a12 = model.predict(net, X12)
            p_se.append(a_se); p8.append(a8); p12.append(a12)
            aucs8.append(evaluate.auc(a8, y8))
            aucs12.append(evaluate.auc(a12, y12))
        # averaging over seeds is already a small council of one architecture
        store[name] = {
            "hidden": hidden, "params": n_params,
            "se": np.mean(p_se, axis=0), "d8": np.mean(p8, axis=0), "d12": np.mean(p12, axis=0),
        }
        m8, s8 = float(np.mean(aucs8)), float(np.std(aucs8))
        m12, s12 = float(np.mean(aucs12)), float(np.std(aucs12))
        rows.append((name, n_params, m8, s8, m12, s12))
        print(f"{name:<22}{n_params:>7}{m8:>9.5f}+-{s8:.5f}{m12:>10.5f}+-{s12:.5f}")

    print(f"\ntrained {len(ARCHS)*len(SEEDS)} networks in total in {time.time()-t0:.0f} s")

    print("\n=== top ten by the hard day ===")
    for name, n, m8, s8, m12, s12 in sorted(rows, key=lambda r: -r[4])[:10]:
        print(f"  {name:<22}{n:>7} weights   d12 {m12:.5f}+-{s12:.5f}   d8 {m8:.5f}")

    np.save(ROOT / "results/_sweep_store.npy", store, allow_pickle=True)
    print("\npredictions saved for assembling the council")


if __name__ == "__main__":
    main()
