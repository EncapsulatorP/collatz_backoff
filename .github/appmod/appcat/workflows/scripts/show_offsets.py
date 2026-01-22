#!/usr/bin/env python3
from collatz_backoff import BackoffConfig, CollatzBackoff

def main():
    cfg = BackoffConfig(
        slots_M=64,
        slot_ms=1,
        base_seconds=0.05,
        collatz_seed=27,
        cap_seconds=10.0,
    )
    b = CollatzBackoff(cfg)

    ids = [0, 1, 2, 3, 7, 13]
    steps = [0, 1, 2, 3, 4, 5]

    print("Collatz-seeded offsets + waits")
    print("cfg:", cfg)
    print()

    for k in steps:
        a, bb = b.affine_params(k)
        print(f"retry k={k} -> a={a}, b={bb}")
        for i in ids:
            slot = b.offset_slot(i, k)
            w = b.wait_seconds(i, k)
            print(f"  id={i:2d} slot={slot:3d} wait={w:.4f}s")
        print()

if __name__ == "__main__":
    main()
