#!/usr/bin/env python3
"""Example 06 · Tier 0: Clone & Run — Decision as a Function (REST + SSE + WebSocket).

Three protocols backed by the same in-process runtime. All decisions are
made by the runtime; the network layer is just transport.
"""

import asyncio
import json
import time
import urllib.request

from helixor_runtime import HelixorEngine
from helixor_runtime.server import start_server, stop_server


def demo_rest(base_url: str) -> None:
    print("\n" + "=" * 75)
    print(" [1] REST: POST /v1/evaluate")
    print("=" * 75)

    payload = json.dumps({
        "text": "Contact CFO at cfo@enterprise.com or call (415) 555-0144."
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/v1/evaluate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req) as resp:
        ms = (time.perf_counter() - t0) * 1000
        res = json.loads(resp.read())
    print(f"  HTTP Roundtrip:    {ms:.2f} ms")
    print(f"  Engine Latency:    {res['latency_us']:.1f} µs")
    print(f"  Action:            {res['action']}")
    print(f'  Sanitized:         "{res["remedy"]["clean_text"]}"')


def demo_sse(base_url: str) -> None:
    print("\n" + "=" * 75)
    print(" [2] SSE: POST /v1/evaluate/stream")
    print("=" * 75)

    payload = json.dumps({
        "text": "Reach support at support@corp.com or security@corp.com.",
        "chunk_size": 4,
        "block_on_fatal": True,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/v1/evaluate/stream",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            decoded = line.decode().strip()
            if decoded.startswith("data: "):
                event = json.loads(decoded[6:])
                badge = " [REDACTED]" if event.get("redacted") else ""
                print(f"    SSE #{event['chunk_index']:02d}: {event['text']!r}{badge}")


async def demo_websocket(base_url: str) -> None:
    import websockets

    print("\n" + "=" * 75)
    print(" [3] WebSocket: WS /v1/ws/decision")
    print("=" * 75)

    ws_url = base_url.replace("http://", "ws://") + "/v1/ws/decision"

    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"type": "ping"}))
        pong = json.loads(await ws.recv())
        print(f"  ✓ Connected: {pong}")

        await ws.send(json.dumps({
            "type": "evaluate",
            "text": "Cardholder PAN 4111-1111-1111-1111 submitted.",
        }))
        verdict = json.loads(await ws.recv())
        print(f"  Action:     {verdict['action']}")
        print(f'  Clean Text: "{verdict["clean_text"]}"')
        print(f"  Latency:    {verdict['latency_us']:.1f} µs")


def main() -> None:
    print("=" * 80)
    print("HELIXOR DECISION RUNTIME — DECISION AS A FUNCTION")
    print("REST · SSE · WebSocket — Same runtime, three transports")
    print("=" * 80)

    engine = HelixorEngine()
    server, thread, base_url = start_server(engine, host="127.0.0.1", port=0)
    print(f"\n✓ Runtime serving on: {base_url}")

    try:
        demo_rest(base_url)
        demo_sse(base_url)
        asyncio.run(demo_websocket(base_url))

        print("\n" + "=" * 80)
        print("ALL PROTOCOLS DEMONSTRATED SUCCESSFULLY.")
        print("=" * 80)
    finally:
        stop_server(server, thread)


if __name__ == "__main__":
    main()
