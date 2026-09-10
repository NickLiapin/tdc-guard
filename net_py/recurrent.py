"""Recurrent network over the sequence of one host's windows.

An LSTM cannot simply replace the MLP on a fixed vector - there is nothing to
unroll. But every host has a SEQUENCE of windows by the hour, and that is what
recurrent memory can read: "the node behaved like this, then like this, then
suddenly differently".

We already tried accumulating suspicion by hand and failed (AUC 0.504). Here the
memory is not set by a rule but learned.

Prediction is made at every step of the sequence, so the comparison with window
models stays apples-to-apples.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).parent))
import data, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEDS = [7, 17, 27]
MAXLEN = 24  # a day in hours


def to_sequences(path: str):
    """Windows -> per-host sequences ordered by time."""
    with open(path, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split(",")
    idx = {n: i for i, n in enumerate(header)}
    raw, y, slots = data.read_csv(path)
    X = data.encode(raw)
    # the src column is read separately: read_csv does not return it
    srcs = []
    with open(path, encoding="utf-8") as fh:
        fh.readline()
        for line in fh:
            srcs.append(line.split(",", 1)[0])
    order = np.lexsort((slots, np.array(srcs)))
    X, y, srcs_a = X[order], y[order], np.array(srcs)[order]

    seqs, labels, index = [], [], []
    start = 0
    for i in range(1, len(srcs_a) + 1):
        if i == len(srcs_a) or srcs_a[i] != srcs_a[start]:
            for a in range(start, i, MAXLEN):
                b = min(a + MAXLEN, i)
                seqs.append(X[a:b]); labels.append(y[a:b]); index.append(np.arange(a, b))
            start = i
    return seqs, labels, index, y


def pad(seqs, labels):
    n, d = len(seqs), seqs[0].shape[1]
    Xp = np.zeros((n, MAXLEN, d), dtype=np.float32)
    Yp = np.zeros((n, MAXLEN), dtype=np.float32)
    Mp = np.zeros((n, MAXLEN), dtype=np.float32)
    for i, (s, l) in enumerate(zip(seqs, labels)):
        k = len(s)
        Xp[i, :k], Yp[i, :k], Mp[i, :k] = s, l, 1.0
    return Xp, Yp, Mp


class Recur(nn.Module):
    def __init__(self, n_in, hidden=24, kind="lstm"):
        super().__init__()
        cls = nn.LSTM if kind == "lstm" else nn.GRU
        self.rnn = cls(n_in, hidden, batch_first=True)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x):
        h, _ = self.rnn(x)
        return self.head(h).squeeze(-1)

    @property
    def n_params(self):
        return sum(p.numel() for p in self.parameters())


def run(kind: str, hidden: int):
    Xtr, ytr, _, _ = to_sequences(str(ROOT / "results/synth-train-windows.csv"))
    Xp, Yp, Mp = pad(Xtr, ytr)
    pos = Yp[Mp > 0].sum()
    tot = Mp.sum()
    pw = torch.tensor((tot - pos) / pos, dtype=torch.float32)

    evals = []
    for path, name in ((str(ROOT / "results/day8-shared.csv"), "day 8"),
                       (str(ROOT / "results/day12-frozen-windows.csv"), "day 12")):
        evals.append((name, *to_sequences(path)))

    a8, a12, npar = [], [], 0
    for seed in SEEDS:
        torch.manual_seed(seed)
        net = Recur(Xp.shape[2], hidden, kind)
        npar = net.n_params
        opt = torch.optim.Adam(net.parameters(), lr=3e-3)
        lf = nn.BCEWithLogitsLoss(pos_weight=pw, reduction="none")
        Xt, Yt, Mt = map(torch.from_numpy, (Xp, Yp, Mp))
        g = torch.Generator().manual_seed(seed)
        for _ in range(60):
            perm = torch.randperm(len(Xt), generator=g)
            for i in range(0, len(perm), 64):
                b = perm[i : i + 64]
                opt.zero_grad()
                loss = (lf(net(Xt[b]), Yt[b]) * Mt[b]).sum() / Mt[b].sum()
                loss.backward()
                opt.step()

        for slot, (name, seqs, labels, index, yflat) in zip((a8, a12), evals):
            Xe, _, Me = pad(seqs, labels)
            scores = np.zeros(len(yflat), dtype=np.float32)
            with torch.no_grad():
                for i in range(0, len(Xe), 512):
                    out = torch.sigmoid(net(torch.from_numpy(Xe[i : i + 512]))).numpy()
                    for j, ix in enumerate(index[i : i + 512]):
                        scores[ix] = out[j, : len(ix)]
            slot.append(evaluate.auc(scores, yflat))

    f = lambda a: f"{np.mean(a):.5f}+-{np.std(a):.5f}"
    print(f"{kind.upper()} hidden={hidden:<4}{npar:>7} parameters   day 8 {f(a8)}   day 12 {f(a12)}")


if __name__ == "__main__":
    print("recurrent networks over a host's sequence of windows\n")
    for kind in ("lstm", "gru"):
        for hidden in (12, 24, 48):
            run(kind, hidden)
