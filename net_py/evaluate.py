"""Quality measures. Computed from ranks in one pass: the held-out set is
3.6M windows, and pairwise comparison is out of the question there.
"""
from __future__ import annotations

import numpy as np


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """ROC AUC via ranks (Mann-Whitney statistic), ties accounted for."""
    order = np.argsort(scores, kind="mergesort")
    s = scores[order]
    ranks = np.empty(len(s), dtype=np.float64)
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        ranks[i:j] = (i + 1 + j) / 2.0  # mean rank for a group of ties
        i = j
    lab = labels[order]
    n_pos = float(lab.sum())
    n_neg = len(lab) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return (ranks[lab == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def cost_curve(scores: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """How many false alarms on the way to the N-th caught window.

    Returns an array where element N-1 is the number of false alarms before the N-th hit.
    This is what the analyst sees: "to find this many, look through this many".
    """
    order = np.argsort(-scores, kind="mergesort")
    lab = labels[order]
    fp = np.cumsum(lab == 0)
    return fp[lab == 1]


def ranks_of_positives(scores: np.ndarray, labels: np.ndarray) -> np.ndarray:
    order = np.argsort(-scores, kind="mergesort")
    pos_at = np.flatnonzero(labels[order] == 1) + 1
    return pos_at


def summary(scores: np.ndarray, labels: np.ndarray) -> dict:
    cost = cost_curve(scores, labels)
    n_pos = int(labels.sum())
    q = lambda frac: int(cost[min(int(np.ceil(n_pos * frac)) - 1, n_pos - 1)])
    return {
        "n": len(labels),
        "pos": n_pos,
        "auc": auc(scores, labels),
        "worst_rank": int(ranks_of_positives(scores, labels)[-1]),
        "fp_at_25": q(0.25),
        "fp_at_50": q(0.50),
        "fp_at_75": q(0.75),
        "fp_at_all": int(cost[-1]),
    }


def fmt(name: str, s: dict) -> str:
    return (
        f"{name:<26} AUC {s['auc']:.5f}  "
        f"false alarms before {int(np.ceil(s['pos']*0.25))}/{s['pos']}: {s['fp_at_25']:>7}  "
        f"before {int(np.ceil(s['pos']*0.5))}: {s['fp_at_50']:>7}  "
        f"before all: {s['fp_at_all']:>8}  worst rank {s['worst_rank']:>8}"
    )
