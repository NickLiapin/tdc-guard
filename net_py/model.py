"""The model and its training. The architecture is given as a list of hidden
layer widths, so experiments with capacity and depth are set up with one parameter.
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn


class MLP(nn.Module):
    def __init__(self, n_in: int, hidden: list[int]):
        super().__init__()
        layers: list[nn.Module] = []
        prev = n_in
        for h in hidden:
            layers += [nn.Linear(prev, h), nn.ReLU()]
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x).squeeze(-1)

    @property
    def n_params(self) -> int:
        return sum(p.numel() for p in self.parameters())


def train(
    X: np.ndarray, y: np.ndarray, hidden: list[int],
    epochs: int = 120, batch: int = 128, lr: float = 3e-3, seed: int = 7,
) -> MLP:
    """Training on synthetic data only. The rare class is weighted, otherwise the
    network learns the profitable strategy of 'always stay silent'."""
    torch.manual_seed(seed)
    model = MLP(X.shape[1], hidden)
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    pos = float(y.sum())
    pos_weight = torch.tensor((len(y) - pos) / max(pos, 1.0), dtype=torch.float32)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    Xt = torch.from_numpy(X)
    yt = torch.from_numpy(y)
    n = len(yt)
    g = torch.Generator().manual_seed(seed)

    model.train()
    for _ in range(epochs):
        order = torch.randperm(n, generator=g)
        for i in range(0, n, batch):
            idx = order[i : i + batch]
            opt.zero_grad()
            loss = loss_fn(model(Xt[idx]), yt[idx])
            loss.backward()
            opt.step()
    return model


@torch.no_grad()
def predict(model: MLP, X: np.ndarray, chunk: int = 200_000) -> np.ndarray:
    """Probabilities in batches: the held-out set is 3.6M rows."""
    model.eval()
    out = []
    for i in range(0, len(X), chunk):
        logits = model(torch.from_numpy(X[i : i + chunk]))
        out.append(torch.sigmoid(logits).numpy())
    return np.concatenate(out)
