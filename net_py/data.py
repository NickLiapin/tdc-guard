"""Loading windows and encoding features.

The only place where features become numbers for the network. The same code
encodes both synthetic windows and real ones: if the encoding is wrong, it is
wrong the same way on both sides, and the comparison stays fair.

One dependency - numpy. The CSV is read by hand: the held-out set file has
3.6M rows, and extra wrappers only get in the way here.
"""
from __future__ import annotations

import numpy as np

# Order matters: it fixes what is fed to the network.
FEATURES = [
    # volume and variety of the window
    "events", "users", "dsts", "newUsers", "newDsts",
    # novelty shares - how much in the window is unfamiliar
    "newUserRatio", "newDstRatio", "newEdgeRatio",
    "failRatio", "rhythm",
    # node context: is it a server or a quiet workstation
    "historySize", "knownUsers",
    # event-level features: a ratio drowns a single event,
    # so ABSOLUTE counts go next to them
    "userSrcNewRatio", "tripleNewCount", "tripleNewRatio", "minUserScope",
    "movedUserCount", "freshUserCount",
]

# Counters are taken under a logarithm: the volumes of the synthetic world and
# the real network differ by orders of magnitude; the logarithm transfers, the raw number does not.
LOG_FEATURES = {
    "events", "users", "dsts", "newUsers", "newDsts",
    "historySize", "knownUsers", "tripleNewCount", "minUserScope",
    "movedUserCount", "freshUserCount",
}
LOG_SCALE = 8.0
RHYTHM_CLIP = 8.0


def read_csv(path: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reads a table of windows.

    Returns (features in original units, labels, slot numbers).
    """
    with open(path, "r", encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split(",")
        idx = {name: i for i, name in enumerate(header)}
        missing = [c for c in FEATURES if c not in idx]
        if missing:
            raise ValueError(f"the table lacks features: {missing} - recompute with the measurer")
        want = [idx[c] for c in FEATURES]
        i_label, i_slot = idx["label"], idx["slot"]

        raw, labels, slots = [], [], []
        for line in fh:
            p = line.rstrip("\n").split(",")
            raw.append([float(p[i]) for i in want])
            labels.append(float(p[i_label]))
            slots.append(int(p[i_slot]))

    return (
        np.asarray(raw, dtype=np.float64),
        np.asarray(labels, dtype=np.float32),
        np.asarray(slots, dtype=np.int64),
    )


def encode(raw: np.ndarray) -> np.ndarray:
    """Original quantities -> network input (N, 18), float32."""
    out = raw.copy()
    for j, name in enumerate(FEATURES):
        if name in LOG_FEATURES:
            out[:, j] = np.log1p(np.clip(out[:, j], 0, None)) / LOG_SCALE
        elif name == "rhythm":
            out[:, j] = np.clip(out[:, j], 0, RHYTHM_CLIP) / RHYTHM_CLIP
    return out.astype(np.float32)


def load(path: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ready (X, y, slots) for training or evaluation."""
    raw, y, slots = read_csv(path)
    return encode(raw), y, slots
