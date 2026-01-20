#!/usr/bin/env python3
"""
Collatz-seeded collision-free backoff (per retry step)

Key idea:
- To guarantee "no collisions at step k", you must assign each participant a unique slot.
- We do that with a bijection (affine permutation) mod M:
    offset_k(id) = (a_k * id + b_k) mod M
- Collatz is only used to generate (a_k, b_k) cheaply per step k.

Collision-free condition:
- id values must be distinct modulo M
- M must be >= max number of participants (e.g., replicas)
- Choose M as a power of two (e.g., 1024), then any odd a_k is invertible.

This gives deterministic de-synchronization without RNG.
"""

from __future__ import annotations
import os
import re
import time
from dataclasses import dataclass


# --------------------------
# Collatz iterator (shortcut)
# --------------------------
def collatz_step(n: int) -> int:
    """One Collatz step (with /2 shortcut on odd branch)."""
    return n // 2 if (n % 2 == 0) else (3 * n + 1) // 2


def collatz_iter(seed: int, k: int) -> int:
    """Iterate Collatz k times."""
    n = int(seed)
    for _ in range(k):
        n = collatz_step(n)
    return n


# ------------------------------------------
# Per-step affine permutation params from Collatz
# ------------------------------------------
def affine_params_from_collatz(k: int, seed: int, M: int) -> tuple[int, int]:
    """
    Returns (a_k, b_k) where a_k is invertible mod M.
    If M is power-of-two, any odd a_k is invertible.
    """
    n = collatz_iter(seed, k + 1)

    # force odd a_k
    a = int((n | 1) % M)
    if a == 0:
        a = 1

    # b_k can be any residue
    b = int((n >> 3) % M)
    return a, b


def collatz_perm_offset(node_id: int, k: int, *, M: int, seed: int) -> int:
    """
    Deterministic per-step offset slot.
    Guaranteed unique for distinct node_id mod M.
    """
    a, b = affine_params_from_collatz(k, seed=seed, M=M)
    return (a * int(node_id) + b) % M


# --------------------------
# Backoff schedule
# --------------------------
@dataclass(frozen=True)
class BackoffConfig:
    base_seconds: float = 0.05       # exponential base (50ms)
    slot_ms: int = 1                 # 1ms slot width
    slots_M: int = 1024              # number of slots (power-of-two recommended)
    collatz_seed: int = 27           # global seed (shared across fleet)
    cap_seconds: float = 10.0        # maximum wait


def collatz_seeded_backoff_seconds(node_id: int, retry_k: int, cfg: BackoffConfig) -> float:
    """
    Backoff(k) = min(cap, base*2^k + offset_k(node_id)*slot_ms)
    """
    offset = collatz_perm_offset(node_id, retry_k, M=cfg.slots_M, seed=cfg.collatz_seed)
    jitter = (offset * cfg.slot_ms) / 1000.0
    wait = (cfg.base_seconds * (2 ** retry_k)) + jitter
    return min(cfg.cap_seconds, wait)


# --------------------------
# Kubernetes helper: parse StatefulSet ordinal
# --------------------------
_ORD_RE = re.compile(r".*-(\d+)$")


def statefulset_ordinal(pod_name: str) -> int:
    """
    Extract ordinal from StatefulSet pod name: "app-3" -> 3
    Falls back to stable hash if not matched.
    """
    m = _ORD_RE.match(pod_name or "")
    if m:
        return int(m.group(1))
    # fallback: deterministic tiny hash
    h = 0
    for ch in (pod_name or "unknown"):
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return int(h)


def sleep_seconds(x: float) -> None:
    """Safe sleep wrapper."""
    if x <= 0:
        return
    time.sleep(x)


def env_int(key: str, default: int) -> int:
    v = os.getenv(key, "").strip()
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def env_float(key: str, default: float) -> float:
    v = os.getenv(key, "").strip()
    if not v:
        return default
    try:
        return float(v)
    except ValueError:
        return default
