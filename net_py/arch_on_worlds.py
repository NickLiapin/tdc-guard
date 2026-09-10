"""Different architectures on merged worlds.

We found a "world x architecture" interaction: the rich world improved the
fully connected network and worsened the recurrent one. So on new data the
ranking of architectures may change too, and all of them must be checked, not one.

Window models (fully connected) and sequence models (recurrent, SSM) are
trained on the same sets and evaluated with the same measures.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402
from recurrent import to_sequences, pad, Recur  # noqa: E402
from exotic import Wrap, DiagSSMBody  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEDS = [7, 17, 27]

SETS = [
    ("base world 400k", "synth-train-windows"),
    ("six worlds merged", "coin-merged-windows"),
]


def eval_window_model(train_csv: str, evals) -> dict:
    """Fully connected network: each window is judged in isolation."""
    X, y, _ = data.load(train_csv)
    out = {}
    for tag, Xe, ye in evals:
        aucs, costs = [], []
        for s in SEEDS:
            net = model.train(X, y, [12] * 8, epochs=120, seed=s)
            p = model.predict(net, Xe)
            aucs.append(evaluate.auc(p, ye)); costs.append(evaluate.cost_curve(p, ye))
        out[tag] = (np.mean(aucs), np.std(aucs), np.median([c[5] for c in costs]))
    return out


def eval_seq_model(train_csv: str, evals_seq, kind: str) -> dict:
    Xtr, ytr, _, _ = to_sequences(train_csv)
    Xp, Yp, Mp = pad(Xtr, ytr)
    pw = torch.tensor(float((Mp.sum() - Yp[Mp > 0].sum()) / Yp[Mp > 0].sum()))
    out = {}
    per_tag = {tag: ([], []) for tag, *_ in evals_seq}
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
        for tag, Xe, index, yflat in evals_seq:
            sc = np.zeros(len(yflat), dtype=np.float32)
            with torch.no_grad():
                for i in range(0, len(Xe), 512):
                    o = torch.sigmoid(net(torch.from_numpy(Xe[i : i + 512]))).numpy()
                    for j, ix in enumerate(index[i : i + 512]):
                        sc[ix] = o[j, : len(ix)]
            per_tag[tag][0].append(evaluate.auc(sc, yflat))
            per_tag[tag][1].append(evaluate.cost_curve(sc, yflat))
    for tag, (a, c) in per_tag.items():
        out[tag] = (np.mean(a), np.std(a), np.median([x[5] for x in c]))
    return out


def main():
    evals, evals_seq = [], []
    for tag, f in (("day 8", "day8-shared"), ("day 12", "day12-frozen-windows")):
        X, y, _ = data.load(str(ROOT / f"results/{f}.csv"))
        evals.append((tag, X, y))
        seqs, labels, index, yflat = to_sequences(str(ROOT / f"results/{f}.csv"))
        Xe, _, _ = pad(seqs, labels)
        evals_seq.append((tag, Xe, index, yflat))

    print(f"{'set':<22}{'model':<16}{'d8 AUC':>10}{'d12 AUC':>18}{'d12 before 6th':>13}")
    print("-" * 80)
    for name, f in SETS:
        p = str(ROOT / f"results/{f}.csv")
        if not Path(p).exists():
            continue
        for mname, fn in (("fully connected", lambda: eval_window_model(p, evals)),
                          ("recurrent", lambda: eval_seq_model(p, evals_seq, "lstm")),
                          ("SSM", lambda: eval_seq_model(p, evals_seq, "ssm"))):
            r = fn()
            a8 = r["day 8"][0]; a12, s12, c12 = r["day 12"]
            print(f"{name:<22}{mname:<16}{a8:>10.5f}{a12:>11.5f}+-{s12:.5f}{int(c12):>13}", flush=True)


if __name__ == "__main__":
    main()
