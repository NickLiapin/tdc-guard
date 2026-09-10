"""CONTROL: six LSTMs on ONE world (the base one), different seeds, mean of ranks.

The ensemble over six DIFFERENT worlds gave 7 false alarms before the 16th on the held-out set.
Question: is that from the different worlds, or simply from averaging six models?
The same ensemble on one world gives the answer.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import evaluate  # noqa: E402
from recurrent import to_sequences, pad  # noqa: E402
from per_world import train_on, score  # noqa: E402
from council import to_ranks  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
world = str(ROOT / "results/synth-train-windows.csv")
print("control: one base world, six seeds", flush=True)
SEALED = ROOT / "results/sealed-windows.csv"
if not SEALED.exists():
    print("results/sealed-windows.csv is missing - the held-out set has not been built yet.\n"
          "exam/sealed.mjs builds it from the slice made by exam/slice-sealed.sh (see README, steps 0 and 1).")
    sys.exit(1)
seqs, labels, index, yflat = to_sequences(str(SEALED))
Xe, _, _ = pad(seqs, labels)
print(f"held-out: {len(yflat)} windows, labelled {int(yflat.sum())}\n", flush=True)

V = []
for seed in (7, 17, 27, 37, 47, 57):
    net = train_on(world, seed=seed)
    V.append(score(net, Xe, index, len(yflat)))
    print(f"  seed {seed}: AUC {evaluate.auc(V[-1], yflat):.5f}", flush=True)
print(f"\nspread of opinions: {float(np.mean(np.std(np.stack(V,1), axis=1))):.5f}")
ens = np.mean([to_ranks(v) for v in V], axis=0)
print(evaluate.fmt("ENSEMBLE, one world", evaluate.summary(ens, yflat)))
c = evaluate.cost_curve(ens, yflat)
print("\nfalse alarms before the N-th hit out of 64:")
print("   N:      1     2     4     8    16    24    32")
print("       " + "".join(f"{int(c[k-1]):>6}" for k in (1, 2, 4, 8, 16, 24, 32)))
print("ensemble of SIX WORLDS:  0     2     2     3     7    19   621")
