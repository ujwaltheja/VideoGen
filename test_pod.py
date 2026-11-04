#!/usr/bin/env python3
"""Smoke-test a RunPod Hub pod (local serverless wrapper on port 80).

  export RUNPOD_API_KEY=...
  python3 test_pod.py nnfcl8uji0ki0e
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.request

# From .runpod/tests.json (tiny PNG)
TEST_IMAGE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAAAwCAIAAAAuKetIAAAAY0lEQVR4nO3PwQkAIBDAsBvRtyM6pUP4CEKhA6Szzv664YIGtKABLWhACxrQgga0oAEtaEALGtCCBrSgAS1oQAsa0IIGtKABLWhACxrQgga0oAEtaEALGtCCBrSgAS1oQAseuxKx8OLAnwX1AAAAAElFTkSuQmCC"
)


def _headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "curl/8.0",
    }


def _req(method: str, url: str, key: str, body: dict | None = None, timeout: int = 900) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=_headers(key),
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def wait_proxy(base: str, key: str, attempts: int = 60, sleep_s: int = 10) -> None:
    health = f"{base}/health"
    for i in range(1, attempts + 1):
        try:
            req = urllib.request.Request(
                health,
                headers={"User-Agent": "curl/8.0"},
            )
            code = urllib.request.urlopen(req, timeout=15).getcode()
            if code == 200:
                print(f"proxy ready after {i} attempt(s)", file=sys.stderr)
                return
        except Exception as exc:
            print(f"[{i}] {health} not ready: {exc}", file=sys.stderr)
        time.sleep(sleep_s)
    sys.exit("pod proxy never became healthy — check container logs")


def main() -> int:
    pod_id = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("POD_ID", "")).strip()
    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not pod_id or not key:
        sys.exit("usage: RUNPOD_API_KEY=... test_pod.py <pod_id>")

    base = f"https://{pod_id}-80.proxy.runpod.net/v2/LOCAL"
    wait_proxy(base, key)

    print("health check...", file=sys.stderr)
    health = _req("POST", f"{base}/runsync", key, {"input": {"health": True}}, timeout=120)
    print("health:", {k: health.get(k, health.get("output", health)) for k in ("status", "output")})

    payload = {
        "input": {
            "prompt": "gentle smile, leaves drifting, camera still",
            "preset": "draft",
            "seconds": 1,
            "seed": 1,
            "steps": 4,
            "image_b64": TEST_IMAGE_B64,
        }
    }
    print("draft clip runsync (may take several minutes on first load)...", file=sys.stderr)
    t0 = time.perf_counter()
    out = _req("POST", f"{base}/runsync", key, payload, timeout=900)
    elapsed = round(time.perf_counter() - t0, 1)
    if out.get("status") != "COMPLETED":
        sys.exit(str(out)[:2000])
    body = out.get("output") or {}
    if body.get("error"):
        sys.exit(body["error"])
    b64 = body.get("video_b64") or ""
    if not b64:
        sys.exit(f"no video in output keys={list(body.keys())}")
    path = f"/tmp/videogen_{pod_id}_test.mp4"
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
    meta = {k: v for k, v in body.items() if k != "video_b64"}
    print(f"ok saved {path} in {elapsed}s meta={meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
