"""Ensemble saturation curve: quality versus the number of networks, random subsets of
the 24 saved scores of the four families on the held-out set."""
import sys
sys.path.insert(0, "net_py")
import numpy as np, data, evaluate
from council import to_ranks
import os
missing = [f for f in ["results/sealed-windows.csv"] + [f"results/{k}-heldout-scores.npy" for k in ("ns", "sp", "st", "nh")] if not os.path.exists(f)]
if missing:
    print("missing files:", ", ".join(missing))
    print("the *-heldout-scores.npy scores are left by net_py/heldout_ensemble.py for each family; run from the repository root")
    sys.exit(1)
raw, y, slots = data.read_csv("results/sealed-windows.csv")
srcs = np.array([l.split(",", 1)[0] for l in open("results/sealed-windows.csv").readlines()[1:]])
y = y[np.lexsort((slots, srcs))]
fams = ("ns", "sp", "st", "nh")
R = np.concatenate([np.stack([to_ranks(np.load(f"results/{k}-heldout-scores.npy")[:, j]) for j in range(6)], 1) for k in fams], 1)
def cost(s, k): return int(evaluate.cost_curve(s, y)[k-1])
rng = np.random.default_rng(3)
print("random subsets of the 24 networks of four families, 12 draws: median [min..max]", flush=True)
print(f"{'nets':>5} {'before 16th':>16} {'before 24th':>16} {'before 32nd':>18}", flush=True)
for k in (1, 2, 3, 4, 6, 8, 12, 16, 24):
    C = {16: [], 24: [], 32: []}
    for _ in range(12 if k < 24 else 1):
        e = R[:, rng.choice(24, k, replace=False)].mean(1)
        for q in C: C[q].append(cost(e, q))
    f = lambda v: f"{int(np.median(v)):5d} [{min(v)}..{max(v)}]"
    print(f"{k:5d} {f(C[16]):>16} {f(C[24]):>16} {f(C[32]):>18}", flush=True)
print("\nsix networks: one family versus a mix of families (12 draws, median before 16/24/32)", flush=True)
picks = {"ns": lambda: rng.choice(6, 6, replace=False), "st": lambda: 12 + rng.choice(6, 6, replace=False), "nh": lambda: 18 + rng.choice(6, 6, replace=False),
         "2 ns+2 st+2 nh": lambda: np.concatenate([rng.choice(6, 2, replace=False), 12 + rng.choice(6, 2, replace=False), 18 + rng.choice(6, 2, replace=False)]),
         "3 ns+3 nh": lambda: np.concatenate([rng.choice(6, 3, replace=False), 18 + rng.choice(6, 3, replace=False)])}
for label, pick in picks.items():
    C = {16: [], 24: [], 32: []}
    for _ in range(12):
        e = R[:, pick()].mean(1)
        for q in C: C[q].append(cost(e, q))
    print(f"  {label:16s} {int(np.median(C[16])):4d} / {int(np.median(C[24])):4d} / {int(np.median(C[32])):5d}", flush=True)
