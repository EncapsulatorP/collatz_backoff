# Collatz-Seeded Backoff (Kubernetes demo)

This repo demonstrates deterministic, collision-free backoff scheduling using a **Collatz-seeded permutation**.

## Why this exists

Standard exponential backoff with random jitter reduces the thundering herd problem, but:
- RNG jitter can clump (collisions)
- fairness is probabilistic
- debugging is harder

Here we use a per-retry-step bijection:

offset_k(id) = (a_k * id + b_k) mod M

where (a_k, b_k) are generated cheaply from Collatz iterations.
This guarantees:
- **no collisions per retry step** (for distinct IDs mod M)
- deterministic replays and debugging
- tiny compute footprint

## Collision-free conditions

- Use a stable numeric ID per pod (StatefulSet ordinal is perfect)
- Ensure `BACKOFF_SLOTS_M >= replicas` (e.g. 1024)
- Choose `BACKOFF_SLOTS_M` as a power-of-two, so any odd `a_k` is invertible

## Run

Build and push image:

```bash
docker build -t YOUR_REPO/collatz-backoff-k8s:latest .
docker push YOUR_REPO/collatz-backoff-k8s:latest
