"""Exotic architectures over a host's sequence of windows.

All of them read the same sequence (up to 24 windows of 18 features) and
predict the label at every step. Training - on synthetic data only.

What we try and why:
  * bidirectional LSTM - sees not only the past but also the future of a window;
  * two-layer LSTM - a hierarchy of time scales;
  * TCN - dilated convolutions, cover the history without recurrence;
  * transformer - self-attention, every window looks at all the others;
  * LMU - memory on Legendre polynomials, an orthogonal basis of the history;
  * diagonal SSM - a simplified S4: linear recurrence with decay;
  * echo state network - a random FROZEN reservoir, only the readout learns;
  * external memory - a simplified neural Turing machine: the network itself
    writes and reads memory cells.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).parent))
import data, evaluate  # noqa: E402
from recurrent import to_sequences, pad, MAXLEN  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEEDS = [7, 17, 27]


class Wrap(nn.Module):
    """Common wrapper: a sequence body + a linear readout."""
    def __init__(self, body, out_dim):
        super().__init__()
        self.body = body
        self.head = nn.Linear(out_dim, 1)

    def forward(self, x):
        return self.head(self.body(x)).squeeze(-1)


class RNNBody(nn.Module):
    def __init__(self, n_in, hidden, kind="lstm", layers=1, bidir=False):
        super().__init__()
        cls = {"lstm": nn.LSTM, "gru": nn.GRU}[kind]
        self.rnn = cls(n_in, hidden, num_layers=layers, batch_first=True, bidirectional=bidir)

    def forward(self, x):
        return self.rnn(x)[0]


class TCNBody(nn.Module):
    """Dilated causal convolutions: the receptive field grows as 2^k without recurrence."""
    def __init__(self, n_in, ch=24, levels=3):
        super().__init__()
        blocks, prev = [], n_in
        for i in range(levels):
            d = 2 ** i
            blocks.append(nn.Sequential(
                nn.ConstantPad1d(((3 - 1) * d, 0), 0.0),   # causal padding
                nn.Conv1d(prev, ch, kernel_size=3, dilation=d),
                nn.ReLU(),
            ))
            prev = ch
        self.net = nn.Sequential(*blocks)

    def forward(self, x):
        return self.net(x.transpose(1, 2)).transpose(1, 2)


class TransformerBody(nn.Module):
    def __init__(self, n_in, d_model=24, heads=4, layers=2):
        super().__init__()
        self.proj = nn.Linear(n_in, d_model)
        pe = torch.zeros(MAXLEN, d_model)
        pos = torch.arange(MAXLEN).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div); pe[:, 1::2] = torch.cos(pos * div)
        self.register_buffer("pe", pe)
        layer = nn.TransformerEncoderLayer(d_model, heads, d_model * 2,
                                           batch_first=True, dropout=0.0)
        self.enc = nn.TransformerEncoder(layer, layers)

    def forward(self, x):
        h = self.proj(x) + self.pe[: x.shape[1]]
        mask = nn.Transformer.generate_square_subsequent_mask(x.shape[1])  # causal
        return self.enc(h, mask=mask)


class LMUBody(nn.Module):
    """Memory on Legendre polynomials: an orthogonal basis of the recent history."""
    def __init__(self, n_in, hidden=16, memory=8, theta=16.0):
        super().__init__()
        self.h, self.m = hidden, memory
        A = np.zeros((memory, memory)); B = np.zeros((memory, 1))
        for i in range(memory):
            B[i] = (-1.0) ** i * (2 * i + 1)
            for j in range(memory):
                A[i, j] = (2 * i + 1) * (-1 if i < j else (-1.0) ** (i - j + 1))
        self.register_buffer("A", torch.tensor(np.eye(memory) + A / theta, dtype=torch.float32))
        self.register_buffer("B", torch.tensor(B / theta, dtype=torch.float32))
        self.e_x = nn.Linear(n_in, 1, bias=False)
        self.e_h = nn.Linear(hidden, 1, bias=False)
        self.W_x = nn.Linear(n_in, hidden, bias=False)
        self.W_h = nn.Linear(hidden, hidden, bias=False)
        self.W_m = nn.Linear(memory, hidden, bias=False)

    def forward(self, x):
        B_, T, _ = x.shape
        h = x.new_zeros(B_, self.h); m = x.new_zeros(B_, self.m)
        out = []
        for t in range(T):
            u = self.e_x(x[:, t]) + self.e_h(h)
            m = m @ self.A.T + u @ self.B.T
            h = torch.tanh(self.W_x(x[:, t]) + self.W_h(h) + self.W_m(m))
            out.append(h)
        return torch.stack(out, 1)


class DiagSSMBody(nn.Module):
    """Simplified S4: diagonal linear recurrence with learnable decay."""
    def __init__(self, n_in, state=32):
        super().__init__()
        self.proj = nn.Linear(n_in, state)
        self.log_decay = nn.Parameter(torch.linspace(-4.0, -0.3, state))
        self.mix = nn.Linear(state + n_in, state)

    def forward(self, x):
        u = self.proj(x)
        a = torch.exp(-torch.exp(self.log_decay))          # decay in (0,1)
        s = torch.zeros_like(u[:, 0]); out = []
        for t in range(x.shape[1]):
            s = a * s + u[:, t]
            out.append(torch.relu(self.mix(torch.cat([s, x[:, t]], -1))))
        return torch.stack(out, 1)


class ESNBody(nn.Module):
    """Echo state network: the reservoir is random and FROZEN, only the readout learns."""
    def __init__(self, n_in, res=64, rho=0.9, seed=0):
        super().__init__()
        g = torch.Generator().manual_seed(seed)
        W = torch.randn(res, res, generator=g)
        W *= rho / torch.linalg.eigvals(W).abs().max().real     # spectral radius
        self.register_buffer("W", W)
        self.register_buffer("Win", torch.randn(res, n_in, generator=g) * 0.5)

    def forward(self, x):
        s = x.new_zeros(x.shape[0], self.W.shape[0]); out = []
        for t in range(x.shape[1]):
            s = torch.tanh(s @ self.W.T + x[:, t] @ self.Win.T)
            out.append(s)
        return torch.stack(out, 1)


class MemoryBody(nn.Module):
    """Simplified neural Turing machine: the network itself writes and reads the cells."""
    def __init__(self, n_in, hidden=16, slots=8, width=8):
        super().__init__()
        self.slots, self.width = slots, width
        self.ctrl = nn.GRUCell(n_in + width, hidden)
        self.key = nn.Linear(hidden, width)      # what to look for
        self.write = nn.Linear(hidden, width)    # what to write
        self.gate = nn.Linear(hidden, 1)         # whether to write
        self.h = hidden

    def forward(self, x):
        B_, T, _ = x.shape
        mem = x.new_zeros(B_, self.slots, self.width)
        h = x.new_zeros(B_, self.h); r = x.new_zeros(B_, self.width)
        out = []
        for t in range(T):
            h = self.ctrl(torch.cat([x[:, t], r], -1), h)
            k = self.key(h)
            w = torch.softmax((mem @ k.unsqueeze(-1)).squeeze(-1), -1)   # content-based addressing
            r = (w.unsqueeze(-1) * mem).sum(1)
            g = torch.sigmoid(self.gate(h)).unsqueeze(-1)
            mem = mem * (1 - g * w.unsqueeze(-1)) + g * w.unsqueeze(-1) * self.write(h).unsqueeze(1)
            out.append(h)
        return torch.stack(out, 1)


ARCHS = [
    ("LSTM-24 (current leader)", lambda d: (RNNBody(d, 24), 24)),
    ("bidirectional LSTM-16", lambda d: (RNNBody(d, 16, bidir=True), 32)),
    ("LSTM-24, two layers",     lambda d: (RNNBody(d, 24, layers=2), 24)),
    ("TCN (dilated convolutions)", lambda d: (TCNBody(d, 24, 3), 24)),
    ("transformer, self-attention", lambda d: (TransformerBody(d, 24, 4, 2), 24)),
    ("LMU (Legendre polynomials)", lambda d: (LMUBody(d, 16, 8), 16)),
    ("diagonal SSM (S4-lite)", lambda d: (DiagSSMBody(d, 32), 32)),
    ("echo state net (reservoir)", lambda d: (ESNBody(d, 64), 64)),
    ("external memory (NTM)",   lambda d: (MemoryBody(d, 16, 8, 8), 16)),
]


def main():
    Xtr, ytr, _, _ = to_sequences(str(ROOT / "results/synth-train-windows.csv"))
    Xp, Yp, Mp = pad(Xtr, ytr)
    pw = torch.tensor(float((Mp.sum() - Yp[Mp > 0].sum()) / Yp[Mp > 0].sum()))
    evals = [(n, *to_sequences(str(ROOT / f"results/{f}.csv"))) for n, f in
             (("day 8", "day8-shared"), ("day 12", "day12-frozen-windows"))]
    padded = [(n, *pad(s, l), idx, yf) for n, s, l, idx, yf in evals]

    print(f"{'architecture':<30}{'parameters':>11}{'day 8':>18}{'day 12':>20}")
    print("-" * 80)
    for name, build in ARCHS:
        a8, a12, npar = [], [], 0
        for seed in SEEDS:
            torch.manual_seed(seed)
            body, dim = build(Xp.shape[2])
            net = Wrap(body, dim)
            npar = sum(p.numel() for p in net.parameters() if p.requires_grad)
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
            for slot, (nm, Xe, _, _, index, yflat) in zip((a8, a12), padded):
                scores = np.zeros(len(yflat), dtype=np.float32)
                with torch.no_grad():
                    for i in range(0, len(Xe), 512):
                        o = torch.sigmoid(net(torch.from_numpy(Xe[i : i + 512]))).numpy()
                        for j, ix in enumerate(index[i : i + 512]):
                            scores[ix] = o[j, : len(ix)]
                slot.append(evaluate.auc(scores, yflat))
        f = lambda a: f"{np.mean(a):.5f}+-{np.std(a):.5f}"
        print(f"{name:<30}{npar:>11}{f(a8):>18}{f(a12):>20}", flush=True)


if __name__ == "__main__":
    main()
