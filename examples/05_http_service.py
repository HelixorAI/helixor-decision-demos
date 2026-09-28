#!/usr/bin/env python3
"""Example 05 · Tier 0: Clone & Run — In-VPC HTTP Microservice.

Wrap the enclave as an internal HTTP/SSE microservice so polyglot consumers
(Go, Java, Node.js, C#) can call it over the network. All decision logic
runs inside the enclave — the HTTP layer is just transport.
"""

import json
import time
import urllib.request

from helixor_runtime import HelixorEngine
from helixor_runtime.server import start_server, stop_server


def main():
    print("=" * 80)
    print("HELIXOR DECISION RUNTIME — IN-VPC HTTP MICROSERVICE")
    print("=" * 80)

    engine = HelixorEngine()
    server, thread, base_url = start_server(engine, host="127.0.0.1", port=0)
    print(f"\n  ✓ Enclave serving on: {base_url}")

    try:
        # Health check
        print("\n[1] GET /v1/health")
        with urllib.request.urlopen(f"{base_url}/v1/health") as resp:
            health = json.loads(resp.read())
            print(f"  Status: {health['status']}")

        # Evaluate
        print("\n[2] POST /v1/evaluate")
        payload = json.dumps({
            "text": "Employee note: John Doe SSN is 123-45-6789, email john@acme.com."
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/v1/evaluate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.perf_counter()
        with urllib.request.urlopen(req) as resp:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            result = json.loads(resp.read())
            print(f"  HTTP Roundtrip:    {elapsed_ms:.2f} ms")
            print(f"  Enclave Latency:   {result['latency_us']:.1f} µs")
            print(f"  Action:            {result['action']}")
            print(f'  Clean Text:        "{result["remedy"]["clean_text"]}"')
            print(f"  Audit Receipt:     {result['receipt_hash']}")

        # SSE streaming
        print("\n[3] POST /v1/evaluate/stream (SSE)")
        stream_payload = json.dumps({
            "text": "Payment card: 4111-1111-1111-1111. Processing order now.",
            "chunk_size": 4,
            "block_on_fatal": True,
        }).encode()
        stream_req = urllib.request.Request(
            f"{base_url}/v1/evaluate/stream",
            data=stream_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(stream_req) as resp:
            for line in resp:
                decoded = line.decode().strip()
                if decoded.startswith("data: "):
                    event = json.loads(decoded[6:])
                    print(f"    SSE | Token: {event['text']!r:12s} | Blocked: {event['blocked']}")
                    if event["blocked"]:
                        print(f"    >> Stream halted: {event['reason']}")
                        break

        print("\n" + "=" * 80)

    finally:
        stop_server(server, thread)


if __name__ == "__main__":
    main()
