"""Recurrent network trained on a given world - on the held-out set.

    python3 net_py/heldout_lstm.py results/sparse-windows.csv "sparse"

Training on synthetic data only; the held-out set - evaluation only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).parent))
import data, evaluate  # noqa: E402
from recurrent import to_sequences, pad, Recur  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
train_path, name = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])

Xtr, ytr, _, _ = to_sequences(train_path)
Xp, Yp, Mp = pad(Xtr, ytr)
pw = torch.tensor(float((Mp.sum() - Yp[Mp > 0].sum()) / Yp[Mp > 0].sum()))

print(f"world: {name} - {sum(len(l) for l in ytr)} windows, labelled {sum(int(l.sum()) for l in ytr)}", flush=True)
print("preparing the held-out set...", flush=True)
SEALED = ROOT / "results/sealed-windows.csv"
if not SEALED.exists():
    print("results/sealed-windows.csv is missing - the held-out set has not been built yet.\n"
          "exam/sealed.mjs builds it from the slice made by exam/slice-sealed.sh (see README, steps 0 and 1).")
    sys.exit(1)
seqs, labels, index, yflat = to_sequences(str(SEALED))
Xe, _, _ = pad(seqs, labels)
print(f"held-out: {len(yflat)} windows, labelled {int(yflat.sum())}\n", flush=True)

curves = []
for seed in (7, 17, 27):
    torch.manual_seed(seed)
    net = Recur(Xp.shape[2], 24)
    opt = torch.optim.Adam(net.parameters(), lr=3e-3)
    lf = nn.BCEWithLogitsLoss(pos_weight=pw, reduction="none")
    Xt, Yt, Mt = map(torch.from_numpy, (Xp, Yp, Mp))
    g = torch.Generator().manual_seed(seed)
    for _ in range(60):
        perm = torch.randperm(len(Xt), generator=g)
        for i in range(0, len(perm), 64):
            b = perm[i : i + 64]
            opt.zero_grad()
            ((lf(net(Xt[b]), Yt[b]) * Mt[b]).sum() / Mt[b].sum()).backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
    sc = np.zeros(len(yflat), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, len(Xe), 512):
            o = torch.sigmoid(net(torch.from_numpy(Xe[i : i + 512]))).numpy()
            for j, ix in enumerate(index[i : i + 512]):
                sc[ix] = o[j, : len(ix)]
    print(evaluate.fmt(f"seed {seed}", evaluate.summary(sc, yflat)), flush=True)
    curves.append(evaluate.cost_curve(sc, yflat))

m = np.median(curves, axis=0)
print("\nmedian over seeds - false alarms before the N-th hit out of 64:")
print("   N:      1     2     4     8    16    24    32")
print("       " + "".join(f"{int(m[k-1]):>6}" for k in (1, 2, 4, 8, 16, 24, 32)))
print("\nfor comparison (previous champion, LSTM on the base world):")
print("             3    10    67   102   188   412  3734")
