"""A council of several architectures and a judge on top of it.

Three ways of combining, from simple to complex:
  1. mean of probabilities - naive, suffers from the networks' different calibration;
  2. mean of RANKS - robust to calibration, the networks vote by order;
  3. judge - a small model that learns to weigh the votes.

The judge is trained on the outputs of the base networks computed on the SYNTHETIC
exam (other seed). It never sees real data, and neither do the base networks.
The council's membership is chosen on the working days; the held-out set takes no part.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def to_ranks(x: np.ndarray) -> np.ndarray:
    """Scores -> normalised ranks in [0,1]. Removes calibration differences."""
    order = np.argsort(x, kind="mergesort")
    r = np.empty(len(x), dtype=np.float32)
    r[order] = np.arange(len(x), dtype=np.float32)
    return r / max(len(x) - 1, 1)


def train_judge(P: np.ndarray, y: np.ndarray, seed: int = 3) -> nn.Module:
    """Judge: one hidden layer over the votes. Deliberately small - its job is
    to weigh the opinions, not to learn the task anew."""
    torch.manual_seed(seed)
    judge = nn.Sequential(nn.Linear(P.shape[1], 8), nn.ReLU(), nn.Linear(8, 1))
    opt = torch.optim.Adam(judge.parameters(), lr=5e-3)
    pos = float(y.sum())
    lf = nn.BCEWithLogitsLoss(pos_weight=torch.tensor((len(y) - pos) / pos))
    Pt, yt = torch.from_numpy(P.astype(np.float32)), torch.from_numpy(y)
    g = torch.Generator().manual_seed(seed)
    for _ in range(200):
        idx = torch.randperm(len(yt), generator=g)
        for i in range(0, len(idx), 256):
            b = idx[i : i + 256]
            opt.zero_grad()
            lf(judge(Pt[b]).squeeze(-1), yt[b]).backward()
            opt.step()
    return judge


@torch.no_grad()
def judge_predict(judge: nn.Module, P: np.ndarray) -> np.ndarray:
    out = []
    for i in range(0, len(P), 200_000):
        chunk = torch.from_numpy(P[i : i + 200_000].astype(np.float32))
        out.append(torch.sigmoid(judge(chunk).squeeze(-1)).numpy())
    return np.concatenate(out)


def main() -> None:
    store = np.load(ROOT / "results/_sweep_store.npy", allow_pickle=True).item()
    _, yse, _ = data.load(str(ROOT / "results/synth-exam-windows.csv"))
    _, y8, _ = data.load(str(ROOT / "results/day8-shared.csv"))
    _, y12, _ = data.load(str(ROOT / "results/day12-frozen-windows.csv"))

    # membership is chosen on the working days: take diverse members
    ranked = sorted(store.items(), key=lambda kv: -evaluate.auc(kv[1]["d12"], y12))
    print("=== members by the hard day ===")
    for name, d in ranked[:12]:
        print(f"  {name:<22}{d['params']:>7} weights   d12 {evaluate.auc(d['d12'], y12):.5f}")

    for k in (3, 5, 8):
        members = [name for name, _ in ranked[:k]]
        tot = sum(store[n]["params"] for n in members)
        print(f"\n=== council of {k} ({tot} weights in total) ===")
        print("   " + ", ".join(members))

        for tag, y, key in (("day 8", y8, "d8"), ("day 12", y12, "d12")):
            probs = np.mean([store[n][key] for n in members], axis=0)
            ranks = np.mean([to_ranks(store[n][key]) for n in members], axis=0)
            print(f"  {tag}: mean of probabilities AUC {evaluate.auc(probs, y):.5f}   "
                  f"mean of ranks AUC {evaluate.auc(ranks, y):.5f}")

        # the judge learns on the synthetic exam
        Pse = np.stack([store[n]["se"] for n in members], axis=1)
        judge = train_judge(Pse, yse)
        for tag, y, key in (("day 8", y8, "d8"), ("day 12", y12, "d12")):
            P = np.stack([store[n][key] for n in members], axis=1)
            print(f"  {tag}: JUDGE AUC {evaluate.auc(judge_predict(judge, P), y):.5f}")


if __name__ == "__main__":
    main()
