# Collatz-Seeded Backoff (Kubernetes demo)

Deterministic, collision-free backoff scheduling using a Collatz-seeded affine permutation.

## Why this exists

Standard exponential backoff with random jitter reduces the thundering herd problem, but:
- RNG jitter can clump (collisions)
- fairness is probabilistic
- debugging is harder

Here we use a per-retry-step bijection:

offset_k(id) = (a_k * id + b_k) mod M

where (a_k, b_k) are generated cheaply from Collatz iterations. This gives:
- no collisions per retry step (for distinct IDs mod M)
- deterministic replays and debugging
- tiny compute footprint

## Collision-free conditions (and proof sketch)

- Use a stable numeric ID per pod (StatefulSet ordinal is perfect)
- Ensure `BACKOFF_SLOTS_M >= replicas`
- Choose `BACKOFF_SLOTS_M` as a power-of-two

An affine map `f(x) = (a * x + b) mod M` is a bijection iff `gcd(a, M) = 1`.
For power-of-two M, any odd `a` is invertible. This implementation forces `a_k` odd
and falls back to `a_k = 1` if `gcd(a_k, M) != 1`.

## Caveats and security notes

- If `replicas > M`, collisions are guaranteed by the pigeonhole principle.
- Deterministic schedules are predictable; for adversarial environments, consider
  a hybrid mode with RNG jitter or per-deploy seed rotation.
- Python integers do not overflow, but large `k` increases compute and wait times;
  the cap limits this.

## Python usage

```python
from collatz_backoff import BackoffConfig, CollatzBackoff

cfg = BackoffConfig(slots_M=1024, slot_ms=1, collatz_seed=27)
b = CollatzBackoff(cfg)
wait_s = b.wait_seconds(node_id=3, retry_k=5)
```

## Demo (local)

```bash
python -m pip install -e .
python demo_client.py
```

Configure with env vars (defaults are in code):
- `POD_NAME`
- `TARGET_URL`
- `BACKOFF_BASE_SECONDS`
- `BACKOFF_SLOT_MS`
- `BACKOFF_SLOTS_M`
- `COLLATZ_SEED`
- `BACKOFF_CAP_SECONDS`
- `MAX_RETRIES`
- `PROBE_TIMEOUT`

## Docker

```bash
docker build -t kugguk2022/collatz_backoff:latest .
docker push EncapsulatorP/collatz_backoff:latest
```

## Kubernetes

Apply the demo manifests:

```bash
kubectl apply -f k8s/
```

The StatefulSet uses the pod name for a stable ordinal ID and runs `demo_client.py`.

## Scripts

Show offsets and waits:

```bash
python scripts/show_offsets.py
```

Compare collision counts against random jitter:

```bash
python scripts/benchmark_jitter.py --slots 1024 --replicas 128 --steps 20
```

Hybrid test mode (deterministic + RNG). This is not collision-free and is only
for benchmarking predictability tradeoffs:

```bash
python scripts/benchmark_jitter.py --mode hybrid --hybrid-prob 0.1
```

## Tests

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

## License

MIT. See `LICENSE`.
