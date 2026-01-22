#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
import random
import urllib.request
import urllib.error

from collatz_backoff import (
    BackoffConfig,
    CollatzBackoff,
    collatz_seeded_backoff_seconds,
    statefulset_ordinal,
    env_int,
    env_float,
)

def http_probe(url: str, timeout: float = 1.0) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", 200)
            return 200 <= code < 300
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False
    except Exception as e:
        print(f"[probe] unexpected error: {e}", flush=True)
        return False

def main() -> int:
    pod_name = os.getenv("POD_NAME", "collatz-demo-0")
    node_id = statefulset_ordinal(pod_name)

    url = os.getenv("TARGET_URL", "http://collatz-backoff-svc:8080/healthz")

    cfg = BackoffConfig(
        base_seconds=env_float("BACKOFF_BASE_SECONDS", 0.05),
        slot_ms=env_int("BACKOFF_SLOT_MS", 1),
        slots_M=env_int("BACKOFF_SLOTS_M", 1024),
        collatz_seed=env_int("COLLATZ_SEED", 27),
        cap_seconds=env_float("BACKOFF_CAP_SECONDS", 10.0),
    )

    max_retries = env_int("MAX_RETRIES", 50)
    timeout = env_float("PROBE_TIMEOUT", 1.0)
    hybrid_prob = env_float("HYBRID_RNG_PROB", 0.0)
    rng_seed = env_int("HYBRID_RNG_SEED", 1337)
    rng = random.Random(rng_seed)
    backoff = CollatzBackoff(cfg)

    print(f"[boot] pod={pod_name} node_id={node_id} url={url} cfg={cfg}", flush=True)

    for k in range(max_retries):
        ok = http_probe(url, timeout=timeout)

        if ok:
            print(f"[ok] pod={pod_name} reached {url} at retry={k}", flush=True)
            return 0

        if hybrid_prob > 0.0 and rng.random() < hybrid_prob:
            offset = rng.randrange(cfg.slots_M)
            base = cfg.base_seconds * (2 ** k)
            jitter = (offset * cfg.slot_ms) / 1000.0
            wait = min(cfg.cap_seconds, base + jitter)
        else:
            wait = collatz_seeded_backoff_seconds(node_id, k, cfg)

        # Print enough info to compare pods
        print(
            f"[retry] pod={pod_name} id={node_id} k={k} wait={wait:.4f}s "
            f"(base={cfg.base_seconds*(2**k):.4f}s + jitter)",
            flush=True,
        )

        time.sleep(wait)

    print(f"[fail] pod={pod_name} exhausted retries={max_retries}", flush=True)
    return 2

if __name__ == "__main__":
    sys.exit(main())
