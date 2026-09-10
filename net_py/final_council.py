"""Final run of the best assembly on the held-out set.

Assembly: the world with an administrator role + a council of three deep networks,
combined by averaging RANKS, three seeds per member (nine networks).

THIRD access to the held-out set. Neither the council's membership, nor the world,
nor the architectures were chosen on it - the choice was made on working days 8 and 12.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402
from council import to_ranks  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEDS = [7, 17, 27]
MEMBERS = [("deep 32x6", [32] * 6), ("deep 16x8", [16] * 8), ("deep 20x6", [20] * 6)]

t0 = time.time()
Xtr, ytr, _ = data.load(str(ROOT / "results/amb-train-windows.csv"))
print(f"training on the world with an administrator: {len(ytr)} windows, labelled {int(ytr.sum())}")

groups, total = [], 0
for name, hidden in MEMBERS:
    nets = [model.train(Xtr, ytr, hidden, epochs=120, seed=s) for s in SEEDS]
    total += nets[0].n_params
    groups.append(nets)
    print(f"  {name}: {nets[0].n_params} weights x {len(SEEDS)} seeds")
print(f"council: {total} weights per member architecture, {len(MEMBERS)*len(SEEDS)} networks in total\n")

raw_s, ys, _ = data.read_csv(str(ROOT / "results/sealed-windows.csv"))
Xs = data.encode(raw_s)
print(f"held-out set: {len(ys)} windows, labelled {int(ys.sum())}\n")

# votes: each architecture - averaged over its own seeds
votes = [np.mean([model.predict(n, Xs) for n in g], axis=0) for g in groups]
for (name, _), v in zip(MEMBERS, votes):
    print(evaluate.fmt(name, evaluate.summary(v, ys)))

council = np.mean([to_ranks(v) for v in votes], axis=0)
print()
print(evaluate.fmt("COUNCIL (ranks)", evaluate.summary(council, ys)))

col = {n: i for i, n in enumerate(data.FEATURES)}
print()
print(evaluate.fmt("counter: accounts", evaluate.summary(raw_s[:, col["users"]], ys)))
print(f"\ntotal {time.time()-t0:.0f} s")
