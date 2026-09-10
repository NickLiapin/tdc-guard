"""Factorial experiment: coincidences x world volume x merging of worlds.

Three factors are checked separately and together, otherwise it is impossible
to tell what exactly gives the gain. The model is the same in every cell - the
recurrent network, the best by the earlier measurements.

Evaluation on the working days; the held-out set is not touched until the winner is chosen.
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
SEEDS = [7, 17, 27]


def coincidences(path: str) -> tuple[int, int, float]:
    """How many normal windows carry the full signature of a compromise."""
    raw, y, _ = data.read_csv(path)
    col = {n: i for i, n in enumerate(data.FEATURES)}
    norm = y == 0
    full = (raw[:, col["newUserRatio"]] >= 0.9) & (raw[:, col["failRatio"]] >= 0.15)
    k, n = int((norm & full).sum()), int(norm.sum())
    return k, n, 100.0 * k / max(n, 1)


def merge(paths: list[str], out: str) -> str:
    """Merges the windows of several worlds into one training set."""
    head, rows = None, []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            h = fh.readline()
            head = head or h
            rows.extend(fh.readlines())
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(head); fh.writelines(rows)
    return out


def run(name: str, train_path: str, evals: list) -> dict:
    Xtr, ytr, _, _ = to_sequences(train_path)
    Xp, Yp, Mp = pad(Xtr, ytr)
    pw = torch.tensor(float((Mp.sum() - Yp[Mp > 0].sum()) / Yp[Mp > 0].sum()))
    res = {tag: [] for tag, *_ in evals}
    for seed in SEEDS:
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
        for tag, Xe, index, yflat in evals:
            sc = np.zeros(len(yflat), dtype=np.float32)
            with torch.no_grad():
                for i in range(0, len(Xe), 512):
                    o = torch.sigmoid(net(torch.from_numpy(Xe[i : i + 512]))).numpy()
                    for j, ix in enumerate(index[i : i + 512]):
                        sc[ix] = o[j, : len(ix)]
            res[tag].append((evaluate.auc(sc, yflat), evaluate.cost_curve(sc, yflat)))
    return res


def main():
    evals = []
    for tag, f in (("d8", "day8-shared"), ("d12", "day12-frozen-windows")):
        seqs, labels, index, yflat = to_sequences(str(ROOT / f"results/{f}.csv"))
        Xe, _, _ = pad(seqs, labels)
        evals.append((tag, Xe, index, yflat))

    cells = []
    base = str(ROOT / "results/synth-train-windows.csv")
    rich = str(ROOT / "results/rich-train-windows.csv")
    cells.append(("base world, 400k, no coincidences", base))
    if Path(rich).exists():
        cells.append(("rich world, 8M, no coincidences", rich))
    coin = sorted(ROOT.glob("results/coin-*-windows.csv"))
    if coin:
        cells.append(("one world with coincidences 1.5%", str(coin[2] if len(coin) > 2 else coin[0])))
        cells.append(("six worlds merged, coincidences 0.5-5%",
                      merge([str(p) for p in coin], str(ROOT / "results/coin-merged-windows.csv"))))

    print(f"{'training set':<40}{'windows':>8}{'coinc.':>9}{'d8 AUC':>10}"
          f"{'d12 AUC':>18}{'d12: before 6th':>14}")
    print("-" * 100)
    for name, path in cells:
        k, n, pct = coincidences(path)
        res = run(name, path, evals)
        a8 = np.mean([a for a, _ in res["d8"]])
        a12 = [a for a, _ in res["d12"]]
        c12 = int(np.median([c[5] for _, c in res["d12"]]))
        print(f"{name:<40}{n:>8}{k:>9}{a8:>10.5f}"
              f"{np.mean(a12):>11.5f}+-{np.std(a12):.5f}{c12:>14}", flush=True)


if __name__ == "__main__":
    main()
