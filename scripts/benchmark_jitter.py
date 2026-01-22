#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
from collections import Counter

from collatz_backoff import BackoffConfig, CollatzBackoff


def run_collatz(slots_M: int, replicas: int, steps: int, seed: int) -> dict[int, int]:
    cfg = BackoffConfig(slots_M=slots_M, collatz_seed=seed, slot_ms=1)
    b = CollatzBackoff(cfg)
    collisions = {}

    for k in range(steps):
        offsets = [b.offset_slot(i, k) for i in range(replicas)]
        collisions[k] = replicas - len(set(offsets))
    return collisions


def run_random(slots_M: int, replicas: int, steps: int, rng_seed: int) -> dict[int, int]:
    rng = random.Random(rng_seed)
    collisions = {}

    for k in range(steps):
        offsets = [rng.randrange(slots_M) for _ in range(replicas)]
        collisions[k] = replicas - len(set(offsets))
    return collisions


def run_hybrid(
    slots_M: int, replicas: int, steps: int, seed: int, rng_seed: int, prob: float
) -> dict[int, int]:
    cfg = BackoffConfig(slots_M=slots_M, collatz_seed=seed, slot_ms=1)
    b = CollatzBackoff(cfg)
    rng = random.Random(rng_seed)
    collisions = {}

    for k in range(steps):
        offsets = []
        for i in range(replicas):
            if rng.random() < prob:
                offsets.append(rng.randrange(slots_M))
            else:
                offsets.append(b.offset_slot(i, k))
        collisions[k] = replicas - len(set(offsets))
    return collisions


def summarize(label: str, collisions: dict[int, int]) -> None:
    counts = Counter(collisions.values())
    worst = max(collisions.values()) if collisions else 0
    print(f"{label} collisions per step: {dict(counts)}")
    print(f"{label} worst-step collisions: {worst}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slots", type=int, default=1024)
    parser.add_argument("--replicas", type=int, default=128)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=27)
    parser.add_argument("--rng-seed", type=int, default=1337)
    parser.add_argument(
        "--mode",
        choices=["collatz", "random", "hybrid", "all"],
        default="all",
        help="Which schedule(s) to benchmark.",
    )
    parser.add_argument(
        "--hybrid-prob",
        type=float,
        default=0.1,
        help="Probability of RNG jitter in hybrid mode.",
    )
    args = parser.parse_args()

    print("Benchmark: collision counts per retry step")
    print(f"slots={args.slots} replicas={args.replicas} steps={args.steps}")
    print()

    if args.mode in ("collatz", "all"):
        collatz = run_collatz(args.slots, args.replicas, args.steps, args.seed)
        summarize("collatz", collatz)

    if args.mode in ("random", "all"):
        rand = run_random(args.slots, args.replicas, args.steps, args.rng_seed)
        summarize("random", rand)

    if args.mode in ("hybrid", "all"):
        hybrid = run_hybrid(
            args.slots, args.replicas, args.steps, args.seed, args.rng_seed, args.hybrid_prob
        )
        summarize(f"hybrid p={args.hybrid_prob:.2f}", hybrid)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
