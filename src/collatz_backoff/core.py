from __future__ import annotations

import os
import re
import math
from dataclasses import dataclass


# --------------------------
# Collatz iterator (shortcut)
# --------------------------
def collatz_step(n: int) -> int:
    """One Collatz step with odd shortcut: (3n+1)/2"""
    return n // 2 if (n % 2 == 0) else (3 * n + 1) // 2


def collatz_iter(seed: int, k: int) -> int:
    """Iterate Collatz k times."""
    n = int(seed)
    for _ in range(k):
        n = collatz_step(n)
    return n


# --------------------------
# Kubernetes helper (StatefulSet ordinal)
# --------------------------
_ORD_RE = re.compile(r".*-(\d+)$")


def statefulset_ordinal(pod_name: str) -> int:
    """
    Extract ordinal from StatefulSet pod name: "app-3" -> 3
    Fallback: deterministic tiny hash if not matched.
    """
    m = _ORD_RE.match(pod_name or "")
    if m:
        return int(m.group(1))

    # fallback hash (stable, low-cost)
    h = 0
    for ch in (pod_name or "unknown"):
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return int(h)


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


# --------------------------
# Backoff primitive
# --------------------------
@dataclass(frozen=True)
class BackoffConfig:
    """
    slots_M:
      - recommended power of two (e.g., 256, 1024)
      - must be >= number of participants for collision-free behavior
    slot_ms:
      - jitter slot size (e.g., 1ms)
    base_seconds:
      - exponential base (e.g., 50ms)
    cap_seconds:
      - hard cap on maximum sleep
    collatz_seed:
      - shared seed across fleet (can be rotated per deploy)
    """
    base_seconds: float = 0.05
    slot_ms: int = 1
    slots_M: int = 1024
    collatz_seed: int = 27
    cap_seconds: float = 10.0

    def validate(self) -> None:
        if self.base_seconds <= 0:
            raise ValueError("base_seconds must be > 0")
        if self.slot_ms <= 0:
            raise ValueError("slot_ms must be > 0")
        if self.slots_M <= 1:
            raise ValueError("slots_M must be > 1")
        if self.cap_seconds <= 0:
            raise ValueError("cap_seconds must be > 0")


class CollatzBackoff:
    """
    Deterministic collision-free backoff per retry step (when conditions hold).

    The core trick:
        offset_k(id) = (a_k * id + b_k) mod M
    where (a_k, b_k) are derived cheaply from a Collatz iterate.

    Collision-free conditions per step k:
      - ids are distinct modulo M
      - M >= number of participants
      - gcd(a_k, M) = 1  (if M is power-of-two, any odd a_k works)
    """

    def __init__(self, cfg: BackoffConfig):
        cfg.validate()
        self.cfg = cfg

    def affine_params(self, k: int) -> tuple[int, int]:
        """
        Return (a_k, b_k). We force a_k invertible mod M.
        If M is power-of-two, odd a_k is invertible.
        """
        M = self.cfg.slots_M
        n = collatz_iter(self.cfg.collatz_seed, k + 1)

        # Force odd, keep in [1..M-1] to avoid 0
        a = int((n | 1) % M)
        if a == 0:
            a = 1

        b = int((n >> 3) % M)

        # Safety: ensure invertibility
        if math.gcd(a, M) != 1:
            # fallback: force a=1 to preserve bijection
            a = 1

        return a, b

    def offset_slot(self, node_id: int, retry_k: int) -> int:
        """Deterministic per-step slot index in [0..M-1]."""
        M = self.cfg.slots_M
        a, b = self.affine_params(retry_k)
        return (a * int(node_id) + b) % M

    def wait_micros(self, node_id: int, retry_k: int) -> int:
        """
        Integer wait time in microseconds (avoids float equality issues).
        """
        base_us = int(round(self.cfg.base_seconds * (2 ** retry_k) * 1_000_000))
        jitter_us = int(self.offset_slot(node_id, retry_k) * self.cfg.slot_ms * 1000)
        cap_us = int(round(self.cfg.cap_seconds * 1_000_000))
        return min(cap_us, base_us + jitter_us)

    def wait_seconds(self, node_id: int, retry_k: int) -> float:
        """Float wait time in seconds."""
        return self.wait_micros(node_id, retry_k) / 1_000_000.0


def collatz_seeded_backoff_seconds(node_id: int, retry_k: int, cfg: BackoffConfig) -> float:
    """
    Compute backoff in seconds using the deterministic Collatz-seeded schedule.
    """
    return CollatzBackoff(cfg).wait_seconds(node_id, retry_k)
