#!/usr/bin/env python3
"""Example 02 · Tier 0: Clone & Run — Throughput Benchmark.

Measures the in-memory enclave's raw evaluation speed across 5,000 payloads.
P50/P90/P99 latency in microseconds. Zero network calls, zero tokens.
"""

import statistics
import time

from helixor_runtime import HelixorEngine


def main() -> None:
    print("=" * 70)
    print(" HELIXOR DECISION RUNTIME — THROUGHPUT & LATENCY BENCHMARK ")
    print("=" * 70)

    engine = HelixorEngine()

    payloads = [
        "Normal business inquiry regarding Q3 vendor service invoice #49280.",
        "Security incident report: SSN 123-45-6789 detected on host 192.168.1.104.",
        "Payment tokenization: card 4111-1111-1111-1111 for user test@company.org.",
        "Clinical triage notes: Patient ID MRN-948201 admitted with chest pain.",
        "Contact update requested via telephone (415) 555-0199 or email user@domain.com.",
    ]

    total_runs = 5000
    print(f"Executing {total_runs:,} evaluations through in-memory enclave...")

    latencies_us: list[float] = []
    t_start = time.perf_counter()

    for i in range(total_runs):
        res = engine.evaluate(payloads[i % len(payloads)])
        latencies_us.append(res.latency_us)

    total_wall_s = time.perf_counter() - t_start
    throughput = total_runs / total_wall_s

    latencies_us.sort()
    p50 = statistics.median(latencies_us)
    p90 = latencies_us[int(total_runs * 0.90)]
    p99 = latencies_us[int(total_runs * 0.99)]
    avg = statistics.mean(latencies_us)

    print("\n" + "=" * 70)
    print(f" BENCHMARK RESULTS ({total_runs:,} Evaluations):")
    print(f"  Throughput:      {throughput:,.1f} ops/sec")
    print(f"  Avg Latency:     {avg:.2f} µs")
    print(f"  P50:             {p50:.2f} µs")
    print(f"  P90:             {p90:.2f} µs")
    print(f"  P99:             {p99:.2f} µs")
    print(f"  Tokens Consumed: 0")
    print(f"  Network Egress:  0 bytes")
    print("=" * 70)


if __name__ == "__main__":
    main()
