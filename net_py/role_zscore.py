"""Peer-class normalisation: does the AUC hold up if features are z-scored within a
host role instead of globally? A question from a reader.

LANL has no inventory, so "role" here is a proxy: hosts are bucketed by the size of
their baseline (historySize) into three classes by quantile - the bottom 60% look like
workstations, the top 5% like servers. Three feature variants, same network:
  raw     - the article's features (log counts, ratios), no standardisation;
  global  - each feature standardised over all windows of the set;
  role    - each feature standardised within its bucket.
Statistics are taken from each set's own windows, no labels used. Training stays on
synthetic data only; the synthetic sets are bucketed by the same quantile rule.

    python3 net_py/role_zscore.py            # fully connected [12]x8, three seeds
    python3 net_py/role_zscore.py --lstm     # plus LSTM-24 on the base world vs the held-out set
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, torch
sys.path.insert(0, str(Path(__file__).parent))
import data, model, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SETS = [("synthetic, other seed", "results/synth-exam-windows.csv", 3), ("day 8", "results/day8-shared.csv", 6),
        ("day 12", "results/day12-frozen-windows.csv", 6), ("held-out", "results/sealed-windows.csv", 16)]
TRAIN = "results/synth-train-windows.csv"
H = data.FEATURES.index("historySize")
ENCODE = data.encode  # the original, so that the LSTM monkeypatch below cannot call itself
Q = (0.60, 0.95)

def roles(raw):
    h = raw[:, H]; t = np.quantile(h, Q)
    return (h > t[0]).astype(int) + (h > t[1]).astype(int)

def standardise(X, groups=None):
    X = X.astype(np.float64).copy()
    if groups is None: groups = np.zeros(len(X), dtype=int)
    for g in np.unique(groups):
        m = groups == g; mu = X[m].mean(0); sd = X[m].std(0); sd[sd < 1e-9] = 1.0
        X[m] = (X[m] - mu) / sd
    return X.astype(np.float32)

def variant(raw, kind):
    X = ENCODE(raw)
    if kind == "raw": return X
    if kind == "global": return standardise(X)
    return standardise(X, roles(raw))

def costs(scores, y, k):
    c = evaluate.cost_curve(scores, y); return int(c[k - 1])

def main():
    raw_tr, y_tr, _ = data.read_csv(str(ROOT / TRAIN))
    if "--lstm-only" in sys.argv: return lstm()

    sets = [(name, *data.read_csv(str(ROOT / p))[:2], k) for name, p, k in SETS]
    print("role buckets by historySize quantiles 0.60 / 0.95; bucket sizes per set:")
    for name, raw, y, k in sets:
        r = roles(raw); print(f"  {name:22s} " + " / ".join(f"{int((r == g).sum())}" for g in range(3)) + f"   labelled per bucket: " + " / ".join(f"{int(y[r == g].sum())}" for g in range(3)))
    print()
    print(f"{'variant':8s} {'seed':>4s}  " + "  ".join(f"{n[:14]:>22s}" for n, *_ in sets))
    print(f"{'':8s} {'':>4s}  " + "  ".join(f"{'AUC / before ' + str(k) + 'th':>22s}" for n, _, _, k in sets))
    agg = {}
    for kind in ("raw", "global", "role"):
        Xtr = variant(raw_tr, kind)
        for seed in (7, 17, 27):
            net = model.train(Xtr, y_tr, [12] * 8, epochs=120, seed=seed)
            row = []
            for name, raw, y, k in sets:
                s = model.predict(net, variant(raw, kind)); a = evaluate.auc(s, y); c = costs(s, y, k)
                row.append(f"{a:.5f} / {c:>6d}"); agg.setdefault((kind, name), []).append((a, c))
            print(f"{kind:8s} {seed:>4d}  " + "  ".join(f"{r:>22s}" for r in row), flush=True)
    print("\nmean over three seeds (AUC +- std / median false alarms):")
    for kind in ("raw", "global", "role"):
        row = []
        for name, raw, y, k in sets:
            v = agg[(kind, name)]; a = np.array([x[0] for x in v]); c = np.array([x[1] for x in v])
            row.append(f"{a.mean():.5f}+-{a.std():.5f} / {int(np.median(c)):>6d}")
        print(f"{kind:8s}       " + "  ".join(f"{r:>22s}" for r in row))
    if "--lstm" in sys.argv: lstm()

def lstm():
    if True:
        from recurrent import to_sequences, pad
        from per_world import train_on, score
        print("\nLSTM-24, base world -> held-out, seed 7:")
        for kind in ("raw", "role"):
            data.encode = (lambda raw, kind=kind: variant(raw, kind)) if kind != "raw" else ENCODE
            torch.manual_seed(7)
            net = train_on(str(ROOT / TRAIN), seed=7)
            seqs, labels, index, y = to_sequences(str(ROOT / "results/sealed-windows.csv"))
            Xe, _, _ = pad(seqs, labels)
            s = score(net, Xe, index, len(y)); c = evaluate.cost_curve(s, y)
            print(f"  {kind:6s} AUC {evaluate.auc(s, y):.5f}  false alarms before 1/8/16/24/32: " + "/".join(str(int(c[k-1])) for k in (1, 8, 16, 24, 32)), flush=True)
        data.encode = ENCODE

if __name__ == "__main__":
    main()
