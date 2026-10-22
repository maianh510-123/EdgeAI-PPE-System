"""Sequential benchmark with raw per-event evidence and explicit loss semantics."""
import csv
import importlib.metadata
import json
import math
import platform
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from edgeai_ppe.benchmark.metrics import latency_metrics
from edgeai_ppe.communication.payload import create_event
from edgeai_ppe.detection.result import Detection


def run_benchmark(client, *, protocol, host, port, output="outputs/communication",
                  messages=100, loss_rate=0.0, seed=42, interval=0.01,
                  measurement="rtt", timeout=5.0, note="", qos=1, topic_prefix="ppe/benchmark"):
    if type(messages) is not int or messages < 1:
        raise ValueError("messages must be a positive integer")
    if not math.isfinite(loss_rate) or not 0 <= loss_rate <= 1:
        raise ValueError("loss_rate must be between 0 and 1")
    if not math.isfinite(interval) or interval < 0:
        raise ValueError("interval must be finite and nonnegative")
    if measurement not in ("rtt", "local-e2e"):
        raise ValueError("Unknown measurement mode")
    if measurement == "local-e2e" and host not in ("127.0.0.1", "localhost"):
        raise ValueError("local-e2e requires a same-OS localhost receiver; use RTT across devices")
    run_id = uuid4().hex
    directory = Path(output) / run_id
    directory.mkdir(parents=True, exist_ok=False)
    rng = random.Random(seed)
    rows = []
    fields = ("sequence", "message_id", "event_timestamp", "status", "start_perf_ns",
              "end_perf_ns", "receiver_perf_ns", "latency_ms", "error")
    with (directory / "raw.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for sequence in range(1, messages + 1):
            event = create_event(Detection("no_helmet", 1.0), "benchmark_sender", "synthetic",
                                 is_demo=True)
            row = dict.fromkeys(fields, "")
            row.update(sequence=sequence, message_id=event.message_id, event_timestamp=event.timestamp)
            if rng.random() < loss_rate:
                row["status"] = "simulated_drop"
            else:
                start = time.perf_counter_ns()
                row["start_perf_ns"] = start
                try:
                    receipt = client.exchange(event)
                    end = time.perf_counter_ns()
                    row["end_perf_ns"] = end
                    row["receiver_perf_ns"] = receipt.receiver_perf_ns
                    if receipt.message_id != event.message_id:
                        raise ValueError("ACK message_id mismatch")
                    boundary = end if measurement == "rtt" else receipt.receiver_perf_ns
                    if boundary < start or (measurement == "local-e2e" and boundary > end):
                        raise ValueError("Receiver clock is not comparable to sender clock")
                    row.update(status="acknowledged", latency_ms=(boundary - start) / 1e6)
                except (OSError, ValueError) as exc:
                    row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                    row["end_perf_ns"] = time.perf_counter_ns()
            writer.writerow(row)
            handle.flush()
            rows.append(row)
            if interval and sequence < messages:
                time.sleep(interval)
    successful = [row["latency_ms"] for row in rows if row["status"] == "acknowledged"]
    drops = sum(row["status"] == "simulated_drop" for row in rows)
    sent = messages - drops
    versions = {}
    for dependency in ("paho-mqtt", "aiocoap"):
        try:
            versions[dependency] = importlib.metadata.version(dependency)
        except importlib.metadata.PackageNotFoundError:
            versions[dependency] = None
    summary = {
        "run_id": run_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "implementation": "reconstructed-testbed-v1", "synthetic_events": True,
        "protocol": protocol, "host": host, "port": port, "measurement": measurement,
        "boundary": ("before exchange -> validated matching application ACK" if measurement == "rtt"
                     else "before exchange -> receiver handler entry after payload is available"),
        "planned_messages": messages, "attempted_sends": sent,
        "simulated_drops": drops, "acknowledged": len(successful), "failed": sent - len(successful),
        "application_ack_rate_planned_pct": 100 * len(successful) / messages,
        "application_ack_rate_sent_pct": 100 * len(successful) / sent if sent else None,
        "loss_rate_requested": loss_rate, "loss_model": "seeded sender event omission, not network packet loss",
        "seed": seed, "interval_seconds_after_exchange": interval, "timeout_seconds": timeout,
        "warmup_messages": 0, "concurrency": 1,
        "session_policy": {"http": "new TCP connection per event; connect included in timer",
                           "mqtt": "preconnected session and ACK subscription; setup excluded",
                           "coap": "reused UDP context; setup excluded"}[protocol],
        "mqtt_qos": qos if protocol == "mqtt" else None,
        "mqtt_topic_prefix": topic_prefix if protocol == "mqtt" else None,
        "p95_method": "linear interpolation at rank 0.95*(N-1)",
        "jitter_method": "mean absolute difference of consecutive successful samples; gaps skipped",
        "note": note, "python": platform.python_version(), "platform": platform.platform(),
        "clock": vars(time.get_clock_info("perf_counter")), "dependencies": versions,
        **latency_metrics(successful),
    }
    (directory / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False,
                                                       allow_nan=False), encoding="utf-8")
    return directory, summary
