import math
import pytest
from hypothesis import given, settings, strategies as st

from collatz_backoff import BackoffConfig, CollatzBackoff


def is_power_of_two(x: int) -> bool:
    return x > 0 and (x & (x - 1)) == 0


@settings(max_examples=80, deadline=None)
@given(
    M=st.sampled_from([8, 16, 32, 64, 128, 256, 512, 1024]),
    seed=st.integers(min_value=1, max_value=10_000),
    k=st.integers(min_value=0, max_value=50),
    n=st.integers(min_value=2, max_value=200),
)
def test_affine_is_bijection_on_id_range(M, seed, k, n):
    """
    For M power-of-two and n <= M, offset_slot(id,k) should be injective over ids [0..n-1].
    """
    assert is_power_of_two(M)
    n = min(n, M)

    cfg = BackoffConfig(slots_M=M, collatz_seed=seed, slot_ms=1)
    b = CollatzBackoff(cfg)

    a, _ = b.affine_params(k)
    assert math.gcd(a, M) == 1  # required for bijection

    ids = list(range(n))
    offsets = [b.offset_slot(i, k) for i in ids]
    assert len(offsets) == len(set(offsets)), "collision: offsets not unique"


@settings(max_examples=60, deadline=None)
@given(
    M=st.sampled_from([32, 64, 128, 256, 512, 1024]),
    seed=st.integers(min_value=1, max_value=10_000),
    n=st.integers(min_value=2, max_value=200),
)
def test_no_wait_collisions_across_multiple_steps(M, seed, n):
    """
    Check that integer wait times are collision-free for each retry step
    over ids [0..n-1], when n <= M.
    """
    n = min(n, M)
    cfg = BackoffConfig(slots_M=M, collatz_seed=seed, slot_ms=1, base_seconds=0.05)
    b = CollatzBackoff(cfg)

    ids = list(range(n))
    for k in range(0, 12):
        waits = [b.wait_micros(i, k) for i in ids]
        assert len(waits) == len(set(waits)), f"collision at retry step k={k}"


def test_documented_constraint_replica_overflow_causes_collisions():
    """
    If you exceed slots_M participants, collisions are unavoidable by pigeonhole principle.
    """
    cfg = BackoffConfig(slots_M=16, collatz_seed=27, slot_ms=1)
    b = CollatzBackoff(cfg)
    ids = list(range(32))  # > M

    offsets = [b.offset_slot(i, 3) for i in ids]
    assert len(offsets) != len(set(offsets)), "should collide when n > M"
