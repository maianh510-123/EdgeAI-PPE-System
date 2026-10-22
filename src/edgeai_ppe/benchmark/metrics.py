"""Explicit statistical definitions; no invented values for empty samples."""
import math
import statistics


def latency_metrics(samples_ms):
    values = list(samples_ms)
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("Latencies must be finite and nonnegative")
    if not values:
        return dict.fromkeys(("mean_ms", "median_ms", "p95_ms", "min_ms", "max_ms", "jitter_ms"))
    ordered = sorted(values)
    rank = .95 * (len(ordered) - 1)
    lower, upper = math.floor(rank), math.ceil(rank)
    p95 = ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)
    jitter = statistics.mean(abs(b - a) for a, b in zip(values, values[1:])) if len(values) > 1 else None
    return {"mean_ms": statistics.mean(values), "median_ms": statistics.median(values),
            "p95_ms": p95, "min_ms": min(values), "max_ms": max(values), "jitter_ms": jitter}
