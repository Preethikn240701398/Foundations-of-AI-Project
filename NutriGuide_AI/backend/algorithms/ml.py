"""Unit V - machine learning building blocks (pure NumPy, no heavy frameworks)."""
import numpy as np


def linear_regression_trend(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Supervised learning: least-squares line y = slope*x + intercept."""
    if len(xs) < 2:
        return 0.0, float(ys[0]) if ys else 0.0
    x, y = np.array(xs, dtype=float), np.array(ys, dtype=float)
    A = np.vstack([x, np.ones(len(x))]).T
    slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
    return float(slope), float(intercept)


def zscore(points: list[list[float]]) -> np.ndarray:
    arr = np.array(points, dtype=float)
    std = arr.std(axis=0)
    std[std == 0] = 1.0
    return (arr - arr.mean(axis=0)) / std


def kmeans(points: list[list[float]], k: int, iterations: int = 60, seed: int = 42):
    """Unsupervised learning: k-means clustering. Returns (labels, centroids)."""
    pts = np.array(points, dtype=float)
    if len(pts) == 0:
        return [], []
    k = max(1, min(k, len(pts)))
    rng = np.random.default_rng(seed)
    centroids = pts[rng.choice(len(pts), k, replace=False)]
    labels = np.zeros(len(pts), dtype=int)
    for _ in range(iterations):
        dist = ((pts[:, None, :] - centroids[None, :, :]) ** 2).sum(-1)
        labels = np.argmin(dist, axis=1)
        new = np.array([pts[labels == i].mean(axis=0) if (labels == i).any() else centroids[i] for i in range(k)])
        if np.allclose(new, centroids):
            break
        centroids = new
    return labels.tolist(), centroids.tolist()


def update_rl_weights(weights: dict, tags: list[str], reward: float, lr: float = 0.1) -> dict:
    """Reinforcement-style update: nudge preference weights for the tags of a meal by +/- reward."""
    out = dict(weights or {})
    for tag in tags or []:
        key = str(tag).lower()
        out[key] = round(float(out.get(key, 0.0)) + lr * reward, 4)
    return out


def score_meal(meal: dict, weights: dict) -> float:
    tags = [str(t).lower() for t in meal.get("tags") or []]
    return sum(float(weights.get(t, 0.0)) for t in tags)
