"""Where the network ranks the normal storms of day 12: a world without storms versus a world with storms.

    python3 net_py/storm_check.py results/sparse-windows.csv results/storm-windows.csv
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, torch
sys.path.insert(0, str(Path(__file__).parent))
import data, evaluate  # noqa: E402
from recurrent import to_sequences, pad  # noqa: E402
from per_world import train_on, score  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
day = str(ROOT / "results/day12-frozen-windows.csv")
seqs, labels, index, y = to_sequences(day)
Xe, _, _ = pad(seqs, labels)
raw, _, slots = data.read_csv(day)
srcs = np.array([l.split(",", 1)[0] for l in open(day).readlines()[1:]])
order = np.lexsort((slots, srcs)); raw, slots, srcs = raw[order], slots[order], srcs[order]
c = {n: i for i, n in enumerate(data.FEATURES)}
storm = (y == 0) & (raw[:, c["events"]] >= 100) & (raw[:, c["failRatio"]] >= 0.9)
print(f"day 12: windows {len(y)}, labelled {int(y.sum())}, normal storms {int(storm.sum())}\n", flush=True)

for w in sys.argv[1:]:
    for seed in (7, 17):
        torch.manual_seed(seed)
        net = train_on(w, seed=seed) if "seed" in train_on.__code__.co_varnames else train_on(w)
        s = score(net, Xe, index, len(y))
        pos = np.empty(len(y), dtype=np.int64); pos[np.argsort(-s, kind="mergesort")] = np.arange(1, len(y) + 1)
        cc = evaluate.cost_curve(s, y)
        print(f"{Path(w).name} seed {seed}: AUC {evaluate.auc(s, y):.5f}; false alarms before 1/2/4/6/8th: "
              + "/".join(str(int(cc[k-1])) for k in (1, 2, 4, 6, 8)))
        print("   storm ranks:", sorted(pos[storm].tolist()))
        print("   ranks of first 8 labelled:", sorted(pos[y == 1].tolist())[:8])
        top = np.argsort(-s, kind="mergesort")[:6]
        print("   top-6:", "; ".join(f"{srcs[i]}@{int(slots[i])} y={int(y[i])} ev={raw[i,c['events']]:.0f} nu={raw[i,c['newUserRatio']]:.2f} f={raw[i,c['failRatio']]:.2f}" for i in top), flush=True)
