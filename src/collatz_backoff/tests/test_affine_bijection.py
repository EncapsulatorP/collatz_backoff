import math
import pytest

from collatz_backoff import BackoffConfig, CollatzBackoff


@pytest.mark.parametrize("M", [4, 8, 16, 32])
@pytest.mark.parametrize("k", [0, 1, 2, 3, 5, 8, 13])
def test_affine_is_bijection_full_range(M: int, k: int) -> None:
    cfg = BackoffConfig(slots_M=M, collatz_seed=27, slot_ms=1)
    b = CollatzBackoff(cfg)

    a, _ = b.affine_params(k)
    assert math.gcd(a, M) == 1

    ids = list(range(M))
    offsets = [b.offset_slot(i, k) for i in ids]
    assert len(offsets) == len(set(offsets))
