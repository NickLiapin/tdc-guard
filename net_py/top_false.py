"""What is left: the top NORMAL windows of the working days for a network trained on a world.

    python3 net_py/top_false.py results/storm-windows.csv

Prints the 40 normal windows with the highest score on days 8 and 12 with their
features, saves the scores to results/<world>-day{8,12}-scores.npy.
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
world = sys.argv[1]; tag = Path(world).name.replace("-windows.csv", "")
torch.manual_seed(7)
net = train_on(world, seed=7)
cols = ["events", "users", "dsts", "newUsers", "newDsts", "newUserRatio", "failRatio", "historySize", "tripleNewCount", "movedUserCount", "freshUserCount"]
c = {n: i for i, n in enumerate(data.FEATURES)}
for dname, f in (("day 8", "day8-shared"), ("day 12", "day12-frozen-windows")):
    day = str(ROOT / f"results/{f}.csv")
    seqs, labels, index, y = to_sequences(day)
    Xe, _, _ = pad(seqs, labels)
    raw, _, slots = data.read_csv(day)
    srcs = np.array([l.split(",", 1)[0] for l in open(day).readlines()[1:]])
    order = np.lexsort((slots, srcs)); raw, slots, srcs = raw[order], slots[order], srcs[order]
    s = score(net, Xe, index, len(y))
    np.save(str(ROOT / f"results/{tag}-{f}-scores.npy"), s)
    cc = evaluate.cost_curve(s, y)
    print(f"\n=== {dname}: AUC {evaluate.auc(s, y):.5f}; false alarms before 1/2/4/6/8/12th: " + "/".join(str(int(cc[k-1])) for k in (1, 2, 4, 6, 8, 12)))
    rank = np.argsort(-s, kind="mergesort")
    pos = np.empty(len(y), dtype=np.int64); pos[rank] = np.arange(1, len(y) + 1)
    print("   ranks of labelled:", sorted(pos[y == 1].tolist())[:16])
    short = {"events": "events", "users": "users", "dsts": "dsts", "newUsers": "newUs", "newDsts": "newDst",
             "newUserRatio": "nuRatio", "failRatio": "failR", "historySize": "history", "tripleNewCount": "tripleN",
             "movedUserCount": "movedUs", "freshUserCount": "freshUs"}
    print(f"   {'rank':>5} {'src':>7} {'slot':>4} " + " ".join(f"{short[n]:>7}" for n in cols))
    shown = 0
    for i in rank:
        if y[i] == 1: continue
        print(f"   {pos[i]:5d} {srcs[i]:>7} {int(slots[i]):4d} " + " ".join(f"{raw[i, c[n]]:7.2f}" for n in cols))
        shown += 1
        if shown >= 40: break
