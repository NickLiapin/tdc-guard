"""Evaluation of one training world on the working days, two architectures.

    python3 net_py/eval_world.py results/sparse-windows.csv "sparse"

Measures: AUC and the price of search (false alarms before the 6th hit on day 12).
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
from exotic import Wrap, DiagSSMBody  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEDS = [7, 17, 27]


def window_shape(path: str) -> str:
    raw, y, _ = data.read_csv(path)
    c = {n: i for i, n in enumerate(data.FEATURES)}
    ev = raw[y == 0, c["events"]]
    q = np.percentile(ev, [1, 50, 90])
    full = (raw[:, c["newUserRatio"]] >= 0.9) & (raw[:, c["failRatio"]] >= 0.15)
    coin = (y == 0) & full
    cshape = f", their median events {np.median(raw[coin, c['events']]):.0f}" if coin.sum() else ""
    return (f"windows {len(y)}, labelled {int(y.sum())}; events per window 1%/50%/90% = "
            f"{q[0]:.0f}/{q[1]:.0f}/{q[2]:.0f}; windows <=2: {100*(ev<=2).mean():.1f}%; "
            f"coincidences {int(coin.sum())}{cshape}")


def run(path: str, kind: str, evals):
    Xtr, ytr, _, _ = to_sequences(path)
    Xp, Yp, Mp = pad(Xtr, ytr)
    pw = torch.tensor(float((Mp.sum() - Yp[Mp > 0].sum()) / Yp[Mp > 0].sum()))
    per = {t: ([], []) for t, *_ in evals}
    for s in SEEDS:
        torch.manual_seed(s)
        net = Recur(Xp.shape[2], 24) if kind == "lstm" else Wrap(DiagSSMBody(Xp.shape[2], 32), 32)
        opt = torch.optim.Adam(net.parameters(), lr=3e-3)
        lf = nn.BCEWithLogitsLoss(pos_weight=pw, reduction="none")
        Xt, Yt, Mt = map(torch.from_numpy, (Xp, Yp, Mp))
        g = torch.Generator().manual_seed(s)
        for _ in range(60):
            perm = torch.randperm(len(Xt), generator=g)
            for i in range(0, len(perm), 64):
                b = perm[i : i + 64]
                opt.zero_grad()
                ((lf(net(Xt[b]), Yt[b]) * Mt[b]).sum() / Mt[b].sum()).backward()
                torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
                opt.step()
        for tag, Xe, index, yflat in evals:
            sc = np.zeros(len(yflat), dtype=np.float32)
            with torch.no_grad():
                for i in range(0, len(Xe), 512):
                    o = torch.sigmoid(net(torch.from_numpy(Xe[i : i + 512]))).numpy()
                    for j, ix in enumerate(index[i : i + 512]):
                        sc[ix] = o[j, : len(ix)]
            per[tag][0].append(evaluate.auc(sc, yflat))
            per[tag][1].append(evaluate.cost_curve(sc, yflat))
    return per


def main():
    path, name = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
    print(f"{name}: {window_shape(path)}\n")
    evals = []
    for tag, f in (("day 8", "day8-shared"), ("day 12", "day12-frozen-windows")):
        seqs, labels, index, yflat = to_sequences(str(ROOT / f"results/{f}.csv"))
        Xe, _, _ = pad(seqs, labels)
        evals.append((tag, Xe, index, yflat))
    print(f"{'model':<14}{'d8 AUC':>10}{'d12 AUC':>18}{'d12: before 1st':>17}{'before 6th':>12}")
    print("-" * 71)
    for kind, label in (("lstm", "recurrent"), ("ssm", "SSM")):
        r = run(path, kind, evals)
        a8 = np.mean(r["day 8"][0]); a12 = r["day 12"][0]
        c = [x for x in r["day 12"][1]]
        c1 = int(np.median([x[0] for x in c])); c6 = int(np.median([x[5] for x in c]))
        print(f"{label:<14}{a8:>10.5f}{np.mean(a12):>11.5f}+-{np.std(a12):.5f}{c1:>17}{c6:>12}", flush=True)


if __name__ == "__main__":
    main()
