import pytest

from collatz_backoff import BackoffConfig, CollatzBackoff


@pytest.mark.parametrize("node_id", [0, 1, 7, 13])
@pytest.mark.parametrize("k", [0, 1, 2, 5, 10, 15])
def test_wait_is_deterministic(node_id: int, k: int) -> None:
    cfg = BackoffConfig(
        slots_M=128,
        slot_ms=1,
        base_seconds=0.05,
        collatz_seed=27,
        cap_seconds=10.0,
    )
    b = CollatzBackoff(cfg)

    w1 = b.wait_micros(node_id, k)
    w2 = b.wait_micros(node_id, k)
    assert w1 == w2

    s1 = b.wait_seconds(node_id, k)
    s2 = b.wait_seconds(node_id, k)
    assert s1 == s2
