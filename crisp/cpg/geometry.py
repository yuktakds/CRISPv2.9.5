from __future__ import annotations

import math

import numpy as np
from scipy.stats import qmc


def quaternion_to_matrix(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64)
    q = q / np.linalg.norm(q)
    w, x, y, z = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def shoemake_quaternions(n: int, seed_offset: int = 0) -> np.ndarray:
    if n <= 0:
        return np.zeros((0, 4), dtype=np.float64)
    sampler = qmc.Sobol(d=3, scramble=False)
    raw = sampler.random_base2(int(math.ceil(math.log2(max(1, n + seed_offset)))))
    u = raw[seed_offset : seed_offset + n]
    if len(u) < n:
        raise RuntimeError("Insufficient Sobol samples for quaternion generation")
    u1 = u[:, 0]
    u2 = u[:, 1]
    u3 = u[:, 2]
    q = np.column_stack(
        [
            np.sqrt(1.0 - u1) * np.sin(2.0 * np.pi * u2),
            np.sqrt(1.0 - u1) * np.cos(2.0 * np.pi * u2),
            np.sqrt(u1) * np.sin(2.0 * np.pi * u3),
            np.sqrt(u1) * np.cos(2.0 * np.pi * u3),
        ]
    ).astype(np.float64)
    q = q[:, [3, 0, 1, 2]]
    return q


def sobol_points_in_ball(n: int, radius: float, dim: int = 3, seed_offset: int = 0) -> np.ndarray:
    if n <= 0:
        return np.zeros((0, dim), dtype=np.float64)
    if dim != 3:
        raise ValueError("Only 3D balls are supported")
    sampler = qmc.Sobol(d=3, scramble=False)
    raw = sampler.random_base2(int(math.ceil(math.log2(max(1, n + seed_offset)))))
    u = raw[seed_offset : seed_offset + n]
    if len(u) < n:
        raise RuntimeError("Insufficient Sobol samples for translation generation")
    r = radius * np.cbrt(u[:, 0])
    phi = 2.0 * np.pi * u[:, 1]
    cos_theta = 2.0 * u[:, 2] - 1.0
    sin_theta = np.sqrt(np.maximum(0.0, 1.0 - cos_theta**2))
    x = r * sin_theta * np.cos(phi)
    y = r * sin_theta * np.sin(phi)
    z = r * cos_theta
    return np.column_stack([x, y, z]).astype(np.float64)
