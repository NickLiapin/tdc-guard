"""Ensemble of six networks (one per ns-world), mean of ranks - on the held-out set."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, torch
sys.path.insert(0, str(Path(__file__).parent))
import evaluate  # noqa: E402
from recurrent import to_sequences, pad  # noqa: E402
from per_world import train_on, score  # noqa: E402
from council import to_ranks  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
prefix = sys.argv[1] if len(sys.argv) > 1 else "ns"
worlds = sorted(ROOT.glob(f"results/{prefix}-[0-9]-windows.csv"))
SEALED = ROOT / "results/sealed-windows.csv"
if not SEALED.exists():
    print("results/sealed-windows.csv is missing - the held-out set has not been built yet.\n"
          "exam/sealed.mjs builds it from the slice made by exam/slice-sealed.sh (see README, steps 0 and 1).")
    sys.exit(1)
if not worlds:
    print(f"no results/{prefix}-0..5-windows.csv files - build the six worlds first: gen/make-*-worlds.sh")
    sys.exit(1)
print(f"worlds: {len(worlds)}", flush=True)
seqs, labels, index, yflat = to_sequences(str(SEALED))
Xe, _, _ = pad(seqs, labels)
print(f"held-out: {len(yflat)} windows, labelled {int(yflat.sum())}\n", flush=True)

V = []
for w in worlds:
    net = train_on(str(w))
    V.append(score(net, Xe, index, len(yflat)))
    print(f"  {w.name}: AUC {evaluate.auc(V[-1], yflat):.5f}", flush=True)
np.save(str(ROOT / f"results/{prefix}-heldout-scores.npy"), np.stack(V, 1))
print(f"\nspread of opinions: {float(np.mean(np.std(np.stack(V, 1), axis=1))):.5f}")
ens = np.mean([to_ranks(v) for v in V], axis=0)
print(evaluate.fmt("ENSEMBLE (ranks)", evaluate.summary(ens, yflat)))
c = evaluate.cost_curve(ens, yflat)
print("\nfalse alarms before the N-th hit out of 64:")
print("   N:      1     2     4     8    16    24    32")
print("       " + "".join(f"{int(c[k-1]):>6}" for k in (1, 2, 4, 8, 16, 24, 32)))
