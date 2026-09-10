"""One network per world, one shared decision.

Earlier ensembles failed for an established reason: all members learned on
ONE world, found one boundary and erred in the same places - the mean spread
of their opinions was 0.0002. There was nothing to average.

Here every network has ITS OWN world: another seed, another coincidence share.
The errors stop being correlated, and combining gains meaning.

Three ways of deciding are checked and, separately, the spread of opinions
itself - it will show whether the cause has been cured.
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
from council import to_ranks, train_judge, judge_predict  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def train_on(path: str, seed: int = 7) -> Recur:
    Xtr, ytr, _, _ = to_sequences(path)
    Xp, Yp, Mp = pad(Xtr, ytr)
    pw = torch.tensor(float((Mp.sum() - Yp[Mp > 0].sum()) / Yp[Mp > 0].sum()))
    torch.manual_seed(seed)
    net = Recur(Xp.shape[2], 24, "lstm")
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
    return net


def score(net: Recur, Xe, index, n: int) -> np.ndarray:
    sc = np.zeros(n, dtype=np.float32)
    with torch.no_grad():
        for i in range(0, len(Xe), 512):
            o = torch.sigmoid(net(torch.from_numpy(Xe[i : i + 512]))).numpy()
            for j, ix in enumerate(index[i : i + 512]):
                sc[ix] = o[j, : len(ix)]
    return sc


def main():
    worlds = sorted(ROOT.glob("results/ns-[0-9]-windows.csv"))
    if not worlds:
        print("worlds are not ready yet"); return
    print(f"worlds: {len(worlds)}\n")

    evals = {}
    for tag, f in (("day 8", "day8-shared"), ("day 12", "day12-frozen-windows")):
        seqs, labels, index, yflat = to_sequences(str(ROOT / f"results/{f}.csv"))
        Xe, _, _ = pad(seqs, labels)
        evals[tag] = (Xe, index, yflat)

    # synthetic exam for training the judge - take a world outside the pool
    ex_path = str(ROOT / "results/rich-exam-windows.csv")
    seqs, labels, ix_ex, y_ex = to_sequences(ex_path)
    Xe_ex, _, _ = pad(seqs, labels)

    nets = [train_on(str(w)) for w in worlds]
    print("networks trained, one per world\n")

    V_ex = np.stack([score(n, Xe_ex, ix_ex, len(y_ex)) for n in nets], axis=1)
    spread = float(np.mean(np.std(V_ex, axis=1)))
    print(f"SPREAD OF OPINIONS between networks: {spread:.5f}")
    print(f"  (networks trained on one world had 0.0002)\n")

    judge = train_judge(V_ex, y_ex)

    print(f"{'method':<34}{'AUC':>10}{'before 1st':>10}{'before 6th':>10}{'before 12th':>11}")
    print("-" * 76)
    for tag, (Xe, index, yflat) in evals.items():
        V = np.stack([score(n, Xe, index, len(yflat)) for n in nets], axis=1)
        best = max(range(V.shape[1]), key=lambda i: evaluate.auc(V[:, i], yflat))
        variants = [
            (f"{tag}: best single", V[:, best]),
            (f"{tag}: mean of ranks", np.mean([to_ranks(V[:, i]) for i in range(V.shape[1])], axis=0)),
            (f"{tag}: judge", judge_predict(judge, V)),
        ]
        for name, sc in variants:
            s = evaluate.summary(sc, yflat)
            c = evaluate.cost_curve(sc, yflat)
            n_pos = int(yflat.sum())
            print(f"{name:<34}{s['auc']:>10.5f}{int(c[0]):>10}"
                  f"{int(c[min(5, n_pos-1)]):>10}{int(c[min(11, n_pos-1)]):>11}")
        print()


if __name__ == "__main__":
    main()
