"""
Train the NeuroPersona OCEAN autoencoder on the IPIP-FFM dataset.

Dataset
    Open-Source Psychometrics Project, "Big Five Personality Test"
    1,015,342 responses to the 50-item IPIP Big-Five Factor Markers.
    Kaggle: https://www.kaggle.com/datasets/tunguz/big-five-personality-test
    Source: https://openpsychometrics.org/_rawdata/  (public domain)

Why this shape
    Training happens once, in PyTorch, on a free Kaggle session. Serving
    happens on every request, in numpy, on a free host. So this script ends by
    exporting plain matrices to a single .npz that backend/model_inference.py
    reads. Production never imports torch.

Session limits
    A Kaggle session is capped at 12 hours and the weekly GPU quota is finite,
    so every epoch writes a checkpoint to OUT_DIR. Re-running the notebook
    picks up where it stopped: save the output as a Kaggle Dataset, attach it
    to the next run, and point RESUME_DIR at it. A full run over ~850k cleaned
    rows finishes well inside one session; the resume path exists so a longer
    or larger run can span a week of sessions without losing work.

Local use
    python train_vae_ocean.py --data path/to/data-final.csv --epochs 30
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone

import numpy as np

# ============================================================================
# THE ITEM BANK
# ============================================================================
# Mirrors backend/ocean_items.py. Kept as a literal so this file runs on Kaggle
# with no repository checkout. backend/test_scoring.py asserts the two agree,
# so drift fails the test suite rather than silently transposing the columns.

ITEM_ORDER = (
    [f'EXT{i}' for i in range(1, 11)]
    + [f'EST{i}' for i in range(1, 11)]
    + [f'AGR{i}' for i in range(1, 11)]
    + [f'CSN{i}' for i in range(1, 11)]
    + [f'OPN{i}' for i in range(1, 11)]
)

TRAIT_ORDER = ['O', 'C', 'E', 'A', 'N']
TRAIT_PREFIX = {'O': 'OPN', 'C': 'CSN', 'E': 'EXT', 'A': 'AGR', 'N': 'EST'}

REVERSED_IDS = frozenset(
    [f'EXT{i}' for i in (2, 4, 6, 8, 10)]
    + [f'EST{i}' for i in (2, 4)]
    + [f'AGR{i}' for i in (1, 3, 5, 7)]
    + [f'CSN{i}' for i in (2, 4, 6, 8)]
    + [f'OPN{i}' for i in (2, 4, 6)]
)

SCALE_MIN, SCALE_MAX = 1, 5

# ============================================================================
# CONFIG
# ============================================================================

KAGGLE_DATA = '/kaggle/input/big-five-personality-test/IPIP-FFM-data-8Nov2018/data-final.csv'
OUT_DIR = '/kaggle/working' if os.path.isdir('/kaggle/working') else './out'

LATENT_DIM = 16
HIDDEN_1 = 128
HIDDEN_2 = 64
N_TYPES = 6
BETA = 0.5          # KL weight; below 1 to keep reconstruction sharp
BATCH_SIZE = 4096
LEARNING_RATE = 1e-3
EPOCHS = 30
VAL_FRACTION = 0.02
SEED = 20260101


# ============================================================================
# DATA
# ============================================================================

def load_responses(path: str, max_rows: int | None = None) -> np.ndarray:
    """Read the 50 item columns and keep only fully answered, in-range rows."""
    import pandas as pd

    print(f'Reading {path}')
    frame = pd.read_csv(path, sep='\t', usecols=ITEM_ORDER, nrows=max_rows,
                        low_memory=False)
    print(f'  {len(frame):,} raw rows')

    values = frame[ITEM_ORDER].apply(pd.to_numeric, errors='coerce').to_numpy(dtype=np.float32)
    del frame

    # 0 marks an unanswered item in this dataset, and NaN marks a parse failure.
    complete = np.all((values >= SCALE_MIN) & (values <= SCALE_MAX), axis=1)
    values = values[complete]
    print(f'  {len(values):,} rows fully answered and in range '
          f'({100 * len(values) / max(complete.size, 1):.1f}%)')

    # Straight-lined sheets carry no signal about trait structure.
    varied = values.std(axis=1) > 0.05
    values = values[varied]
    print(f'  {len(values):,} rows after dropping straight-lined sheets')
    return values


def trait_scores(values: np.ndarray) -> np.ndarray:
    """Trait scores on the same 0-100 scale the backend reports, per row."""
    keyed = values.copy()
    reverse_mask = np.array([item in REVERSED_IDS for item in ITEM_ORDER])
    keyed[:, reverse_mask] = (SCALE_MIN + SCALE_MAX) - keyed[:, reverse_mask]

    out = np.zeros((len(values), len(TRAIT_ORDER)), dtype=np.float32)
    for idx, trait in enumerate(TRAIT_ORDER):
        cols = [i for i, item in enumerate(ITEM_ORDER)
                if item.startswith(TRAIT_PREFIX[trait])]
        out[:, idx] = (keyed[:, cols].mean(axis=1) - SCALE_MIN) / (SCALE_MAX - SCALE_MIN) * 100.0
    return out


# ============================================================================
# MODEL
# ============================================================================

def build_model(torch, nn):
    class VAE(nn.Module):
        """Encoder 50-128-64-16, decoder 16-64-50, tanh throughout.

        The layer shapes are fixed because model_inference.py multiplies these
        exact matrices by hand. Changing them means changing both files.
        """

        def __init__(self):
            super().__init__()
            self.enc1 = nn.Linear(len(ITEM_ORDER), HIDDEN_1)
            self.enc2 = nn.Linear(HIDDEN_1, HIDDEN_2)
            self.mu = nn.Linear(HIDDEN_2, LATENT_DIM)
            self.logvar = nn.Linear(HIDDEN_2, LATENT_DIM)
            self.dec1 = nn.Linear(LATENT_DIM, HIDDEN_2)
            self.dec2 = nn.Linear(HIDDEN_2, len(ITEM_ORDER))

        def encode(self, x):
            h = torch.tanh(self.enc1(x))
            h = torch.tanh(self.enc2(h))
            return self.mu(h), self.logvar(h)

        def decode(self, z):
            return self.dec2(torch.tanh(self.dec1(z)))

        def forward(self, x):
            mu, logvar = self.encode(x)
            std = torch.exp(0.5 * logvar)
            z = mu + std * torch.randn_like(std) if self.training else mu
            return self.decode(z), mu, logvar

    return VAE()


# ============================================================================
# K-MEANS (numpy, so the notebook needs no extra dependency)
# ============================================================================

def kmeans(points: np.ndarray, k: int, iterations: int = 60,
           seed: int = SEED) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)

    # k-means++ seeding.
    centroids = [points[rng.integers(len(points))]]
    for _ in range(k - 1):
        gaps = np.min(
            ((points[:, None, :] - np.array(centroids)[None, :, :]) ** 2).sum(-1), axis=1)
        total = gaps.sum()
        probabilities = gaps / total if total > 0 else None
        centroids.append(points[rng.choice(len(points), p=probabilities)])
    centroids = np.array(centroids)

    labels = np.zeros(len(points), dtype=np.int64)
    for step in range(iterations):
        distances = ((points[:, None, :] - centroids[None, :, :]) ** 2).sum(-1)
        new_labels = distances.argmin(axis=1)
        if step and np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for index in range(k):
            member = points[labels == index]
            if len(member):
                centroids[index] = member.mean(axis=0)
    return centroids, labels


# ============================================================================
# NAMING THE CLUSTERS
# ============================================================================

TRAIT_NAMES = {
    'O': ('The Explorer', 'The Traditionalist'),
    'C': ('The Organiser', 'The Improviser'),
    'E': ('The Connector', 'The Observer'),
    'A': ('The Diplomat', 'The Challenger'),
    'N': ('The Sentinel', 'The Anchor'),
}


def name_clusters(centroid_traits: np.ndarray) -> list[str]:
    """Name each cluster after whichever trait it departs from the mean on.

    The names come out of the data rather than being written in advance, so a
    retrain on different data renames the types instead of mislabelling them.
    """
    overall_mean = centroid_traits.mean(axis=0)
    overall_std = centroid_traits.std(axis=0) + 1e-8
    z = (centroid_traits - overall_mean) / overall_std

    names, taken = [], set()
    for row in z:
        for trait_index in np.argsort(-np.abs(row)):
            trait = TRAIT_ORDER[trait_index]
            high, low = TRAIT_NAMES[trait]
            candidate = high if row[trait_index] >= 0 else low
            if candidate not in taken:
                taken.add(candidate)
                names.append(candidate)
                break
        else:
            fallback = f'Type {len(names) + 1}'
            taken.add(fallback)
            names.append(fallback)
    return names


# ============================================================================
# TRAINING
# ============================================================================

def train(data_path: str = KAGGLE_DATA, out_dir: str = OUT_DIR,
          epochs: int = EPOCHS, resume_dir: str | None = None,
          max_rows: int | None = None) -> str:
    import torch
    from torch import nn

    os.makedirs(out_dir, exist_ok=True)
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Device: {device}')

    values = load_responses(data_path, max_rows=max_rows)
    n_total = len(values)

    feature_mean = values.mean(axis=0)
    feature_std = values.std(axis=0) + 1e-8
    standardised = (values - feature_mean) / feature_std

    rng = np.random.default_rng(SEED)
    shuffle = rng.permutation(n_total)
    split = int(n_total * (1 - VAL_FRACTION))
    train_x = torch.from_numpy(standardised[shuffle[:split]]).float()
    val_x = torch.from_numpy(standardised[shuffle[split:]]).float().to(device)
    print(f'Train {len(train_x):,} · validate {len(val_x):,}')

    model = build_model(torch, nn).to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    start_epoch = 0
    checkpoint_path = os.path.join(out_dir, 'checkpoint.pt')
    resume_from = None
    for candidate in (os.path.join(resume_dir, 'checkpoint.pt') if resume_dir else None,
                      checkpoint_path):
        if candidate and os.path.exists(candidate):
            resume_from = candidate
            break
    if resume_from:
        state = torch.load(resume_from, map_location=device)
        model.load_state_dict(state['model'])
        optimiser.load_state_dict(state['optimiser'])
        start_epoch = state['epoch'] + 1
        print(f'Resumed from {resume_from} at epoch {start_epoch}')

    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(train_x),
        batch_size=BATCH_SIZE, shuffle=True, drop_last=True)

    for epoch in range(start_epoch, epochs):
        model.train()
        started, running = time.time(), 0.0
        for (batch,) in loader:
            batch = batch.to(device, non_blocking=True)
            reconstruction, mu, logvar = model(batch)
            recon_loss = nn.functional.mse_loss(reconstruction, batch, reduction='mean')
            kl = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
            loss = recon_loss + BETA * kl
            optimiser.zero_grad(set_to_none=True)
            loss.backward()
            optimiser.step()
            running += loss.item()

        model.eval()
        with torch.no_grad():
            val_recon, val_mu, val_logvar = model(val_x)
            val_loss = (nn.functional.mse_loss(val_recon, val_x).item()
                        + BETA * (-0.5 * torch.mean(
                            1 + val_logvar - val_mu.pow(2) - val_logvar.exp())).item())

        print(f'epoch {epoch + 1:3d}/{epochs}  train {running / len(loader):.5f}  '
              f'val {val_loss:.5f}  {time.time() - started:.1f}s')

        torch.save({'model': model.state_dict(), 'optimiser': optimiser.state_dict(),
                    'epoch': epoch, 'val_loss': val_loss}, checkpoint_path)

    return export(model, torch, values, standardised, feature_mean, feature_std,
                  out_dir, n_total, epochs, device)


# ============================================================================
# EXPORT
# ============================================================================

def export(model, torch, values, standardised, feature_mean, feature_std,
           out_dir, n_total, epochs, device) -> str:
    print('\nExporting weights')
    model.eval()

    # Latents for a sample large enough to place stable centroids.
    sample_size = min(200_000, len(standardised))
    rng = np.random.default_rng(SEED)
    sample_index = rng.choice(len(standardised), sample_size, replace=False)
    with torch.no_grad():
        sample = torch.from_numpy(standardised[sample_index]).float().to(device)
        latents = model.encode(sample)[0].cpu().numpy()
        reconstruction = model.decode(torch.from_numpy(latents).to(device)).cpu().numpy()
    recon_errors = ((standardised[sample_index] - reconstruction) ** 2).mean(axis=1)

    print(f'  k-means over {sample_size:,} latents')
    centroids, labels = kmeans(latents, N_TYPES)

    scores = trait_scores(values)
    sample_scores = scores[sample_index]
    centroid_traits = np.stack([
        sample_scores[labels == index].mean(axis=0) if np.any(labels == index)
        else sample_scores.mean(axis=0)
        for index in range(N_TYPES)
    ])
    names = name_clusters(centroid_traits)
    for index, name in enumerate(names):
        share = 100 * np.mean(labels == index)
        profile = ', '.join(f'{t} {v:.0f}' for t, v in zip(TRAIT_ORDER, centroid_traits[index]))
        print(f'  {index}: {name:<20} {share:5.1f}%   {profile}')

    trait_quantiles = np.stack([
        np.percentile(scores[:, i], np.arange(101)) for i in range(len(TRAIT_ORDER))
    ])

    weights = {k: v.detach().cpu().numpy() for k, v in model.state_dict().items()}
    path = os.path.join(out_dir, 'ocean_vae.npz')
    np.savez_compressed(
        path,
        item_order=np.array(ITEM_ORDER),
        feature_mean=feature_mean.astype(np.float64),
        feature_std=feature_std.astype(np.float64),
        # torch Linear stores weights as (out, in); the numpy forward pass does
        # x @ W, so every matrix is transposed on the way out.
        enc_w1=weights['enc1.weight'].T.astype(np.float64),
        enc_b1=weights['enc1.bias'].astype(np.float64),
        enc_w2=weights['enc2.weight'].T.astype(np.float64),
        enc_b2=weights['enc2.bias'].astype(np.float64),
        enc_mu_w=weights['mu.weight'].T.astype(np.float64),
        enc_mu_b=weights['mu.bias'].astype(np.float64),
        dec_w1=weights['dec1.weight'].T.astype(np.float64),
        dec_b1=weights['dec1.bias'].astype(np.float64),
        dec_w2=weights['dec2.weight'].T.astype(np.float64),
        dec_b2=weights['dec2.bias'].astype(np.float64),
        centroids=centroids.astype(np.float64),
        centroid_traits=centroid_traits.astype(np.float64),
        type_names=np.array(names),
        latent_mean=latents.mean(axis=0).astype(np.float64),
        latent_std=latents.std(axis=0).astype(np.float64),
        recon_mean=np.float64(recon_errors.mean()),
        recon_std=np.float64(recon_errors.std()),
        trait_quantiles=trait_quantiles.astype(np.float64),
        meta_json=json.dumps({
            'version': datetime.now(timezone.utc).strftime('%Y%m%d'),
            'dataset': 'Open-Source Psychometrics Project IPIP-FFM (data-final.csv)',
            'dataset_url': 'https://www.kaggle.com/datasets/tunguz/big-five-personality-test',
            'n_train': int(n_total),
            'epochs': int(epochs),
            'latent_dim': LATENT_DIM,
            'n_types': N_TYPES,
            'trained_at': datetime.now(timezone.utc).isoformat(),
        }),
    )
    print(f'\nWrote {path} ({os.path.getsize(path) / 1e6:.2f} MB)')
    print('Copy it to backend/model_weights/ocean_vae.npz')
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default=KAGGLE_DATA)
    parser.add_argument('--out', default=OUT_DIR)
    parser.add_argument('--epochs', type=int, default=EPOCHS)
    parser.add_argument('--resume-dir', default=None,
                        help='Attached Kaggle dataset holding a previous checkpoint.pt')
    parser.add_argument('--max-rows', type=int, default=None,
                        help='Read only the first N rows, for a quick smoke run')
    args = parser.parse_args()
    train(args.data, args.out, args.epochs, args.resume_dir, args.max_rows)


if __name__ == '__main__':
    main()
