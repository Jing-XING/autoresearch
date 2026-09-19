"""Public development controls for AutoResearchExam risk estimation.

Trusted in-process baselines only. This is not the official sandbox or grader.
"""
from __future__ import annotations

import hashlib
import numbers
import time

import numpy as np


METHODS = ("uniform", "surrogate_only", "difference")
BUDGETS = (50, 100, 200, 400)
SEEDS = tuple(range(2026091900, 2026091916))


class Uniform:
    def __init__(self, pool, budget, rng):
        self.losses = -np.log(pool["target_probs"])
        self.indices = iter(rng.choice(pool["n_pool"], budget, replace=False))
        self.observed = []

    def next_index(self):
        return int(next(self.indices))

    def observe(self, index, label):
        self.observed.append(float(self.losses[index, label]))

    def estimate(self):
        return float(np.mean(self.observed))


class SurrogateOnly(Uniform):
    def __init__(self, pool, budget, rng):
        super().__init__(pool, budget, rng)
        self.proxy = np.sum(pool["surrogate_probs"] * self.losses, axis=1)

    def estimate(self):
        return float(self.proxy.mean())


class Difference(SurrogateOnly):
    def observe(self, index, label):
        self.observed.append(float(self.losses[index, label] - self.proxy[index]))

    def estimate(self):
        return float(self.proxy.mean() + np.mean(self.observed))


BASELINES = dict(zip(METHODS, (Uniform, SurrogateOnly, Difference)))


def evaluate(factory, target, surrogate, labels, budget, seed, max_seconds=5):
    """Drive the published label API; retain failures and repeated queries.

    Read-only array copies and a fresh instance prevent accidental cross-run
    mutation. This does not isolate hostile code or enforce a hard call timeout.
    """
    n, c = target.shape
    if not 0 < budget <= n or labels.shape != (n,) or surrogate.shape != (n, c):
        raise ValueError("Invalid development input dimensions/budget")
    if not (np.isfinite(target).all() and (target > 0).all()):
        raise ValueError("Finite positive target probabilities required; no clipping")
    if not ((labels >= 0).all() and (labels < c).all()):
        raise ValueError("Invalid labels")
    # Separate, deterministic row permutation; the estimator RNG remains exactly
    # the given seed and is identical across all three methods.
    permutation = np.random.default_rng(np.random.SeedSequence([seed, 7701])).permutation(n)
    target = np.ascontiguousarray(target[permutation])
    surrogate = np.ascontiguousarray(surrogate[permutation])
    labels = labels[permutation]
    target.flags.writeable = surrogate.flags.writeable = False
    truth = float((-np.log(target[np.arange(n), labels])).mean())
    pool = dict(target_probs=target, surrogate_probs=surrogate, n_pool=n, n_classes=c)
    row = dict(seed=seed, budget=budget, true_risk=truth, queries=[], status="ok",
               permutation_sha256=hashlib.sha256(permutation.astype('<i8').tobytes()).hexdigest())
    start = time.monotonic()
    try:
        estimator = factory(pool, budget, np.random.default_rng(seed))
        for _ in range(budget):
            index = estimator.next_index()
            if isinstance(index, (bool, np.bool_)) or not isinstance(index, numbers.Integral):
                raise ValueError("next_index must be an integer")
            index = int(index)
            if not 0 <= index < n:
                raise ValueError("next_index outside pool")
            label = int(labels[index])
            row["queries"].append(dict(index=index, original_index=int(permutation[index]), label=label))
            estimator.observe(index, label)
            if time.monotonic() - start > max_seconds:
                raise TimeoutError("Development elapsed-time limit exceeded")
        estimate = float(estimator.estimate())
        if not np.isfinite(estimate):
            raise ValueError("Non-finite estimate")
        if time.monotonic() - start > max_seconds:
            raise TimeoutError("Development elapsed-time limit exceeded")
        row.update(estimate=estimate, squared_error=float((estimate - truth) ** 2))
    except Exception as exc:
        row.update(status="failed", error=f"{type(exc).__name__}: {exc}",
                   estimate=None, squared_error=None)
    row["duration_seconds"] = time.monotonic() - start
    row["label_calls"] = len(row["queries"])
    row["distinct_labels"] = len({q["index"] for q in row["queries"]})
    return row


def summarize(rows, pools, budgets=BUDGETS, seeds=SEEDS):
    """Median of cell ratios, with failures/zero denominators invalidating score."""
    keyed = {(r["pool"], r["budget"], r["seed"], r["method"]): r for r in rows}
    if len(keyed) != len(rows):
        raise ValueError("Duplicate trial")
    expected = {(p, b, s, m) for p in pools for b in budgets for s in seeds for m in METHODS}
    if set(keyed) != expected:
        raise ValueError("Missing or unexpected trial; never drop cases")
    cells = []
    for pool in pools:
        for budget in budgets:
            selected = {m: [keyed[pool, budget, s, m] for s in seeds] for m in METHODS}
            for seed in seeds:
                matched = [keyed[pool, budget, seed, m] for m in METHODS]
                if len({r["permutation_sha256"] for r in matched}) != 1:
                    raise ValueError("Unmatched permutations")
                if all(r["status"] == "ok" for r in matched):
                    if any(r["queries"] != matched[0]["queries"] for r in matched[1:]):
                        raise ValueError("Control methods must use identical label queries")
            medians = {m: (float(np.median([r["squared_error"] for r in rs]))
                           if all(r["status"] == "ok" for r in rs) else None)
                       for m, rs in selected.items()}
            denominator = medians["uniform"]
            ratios = {m: (v / denominator if v is not None and denominator is not None
                          and denominator > 0 else None) for m, v in medians.items()}
            cells.append(dict(pool=pool, budget=budget, median_squared_error=medians,
                              ratios=ratios, failures={m: sum(r["status"] != "ok" for r in rs)
                                                       for m, rs in selected.items()}))
    scores = {m: (float(np.median([c["ratios"][m] for c in cells]))
                  if all(c["ratios"][m] is not None for c in cells) else None) for m in METHODS}
    return dict(trials=len(rows), cells=cells, median_cell_ratio=scores,
                failures=sum(r["status"] != "ok" for r in rows))
