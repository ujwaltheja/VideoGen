#!/usr/bin/env python3
"""One clip from the RunPod kids image-to-video endpoint.

  export RUNPOD_API_KEY=...
  export VIDEO_EP=your-endpoint-id
  python client.py still.jpg "gentle smile, leaves drifting, camera still" out.mp4
  python client.py --preset draft still.jpg "tiny happy bounce" draft.mp4
  python client.py --seconds 5 --steps 12 still.jpg "Rosie claps, Ollie blinks" long.mp4
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.request

API = "https://api.runpod.ai/v2"


def _req(method: str, url: str, key: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    p = argparse.ArgumentParser(description="Kids clips on RunPod (Wan 2.2 TI2V-5B)")
    p.add_argument("image")
    p.add_argument("prompt")
    p.add_argument("out")
    p.add_argument("--preset", choices=("landscape", "short", "draft"), default="landscape")
    p.add_argument("--width", type=int, default=0)
    p.add_argument("--height", type=int, default=0)
    p.add_argument("--seconds", type=float, default=0)
    p.add_argument("--seed", type=int, default=-1)
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--cfg", type=float, default=5.0)
    p.add_argument("--neg", default="")
    args = p.parse_args()

    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    ep = (
        os.environ.get("VIDEO_EP", "").strip()
        or os.environ.get("I2V_EP", "").strip()
        or os.environ.get("KVS_I2V_EP", "").strip()
    )
    if not key or not ep:
        sys.exit("Set RUNPOD_API_KEY and VIDEO_EP")

    with open(args.image, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "input": {
            "prompt": args.prompt,
            "image_b64": image_b64,
            "preset": args.preset,
            "seed": args.seed,
            "steps": args.steps,
            "cfg": args.cfg,
        },
        "policy": {"ttl": 900000},
    }
    if args.width:
        payload["input"]["width"] = args.width
    if args.height:
        payload["input"]["height"] = args.height
    if args.seconds:
        payload["input"]["seconds"] = args.seconds
    if args.neg:
        payload["input"]["negative_prompt"] = args.neg

    job = _req("POST", f"{API}/{ep}/run", key, payload)
    jid = job["id"]
    print(f"job {jid}", file=sys.stderr)
    waited = 0
    while True:
        status = _req("GET", f"{API}/{ep}/status/{jid}", key)
        st = status.get("status")
        if st == "COMPLETED":
            break
        if st in ("FAILED", "CANCELLED", "TIMED_OUT"):
            sys.exit(str(status.get("error") or status)[:1200])
        time.sleep(5)
        waited += 5
        if waited > 1500:
            sys.exit("timeout waiting for the worker")
    out = status["output"]
    if out.get("error"):
        sys.exit(out["error"])
    b64 = out.get("video_b64") or out.get("video") or ""
    if "," in b64 and b64.lower().startswith("data:"):
        b64 = b64.split(",", 1)[1]
    raw = base64.b64decode(b64)
    with open(args.out, "wb") as f:
        f.write(raw)
    meta = {k: v for k, v in out.items() if k not in ("video_b64", "video")}
    print(f"saved {args.out} {meta} delay_ms={status.get('delayTime')} exec_ms={status.get('executionTime')}")
    try:
        _req("POST", f"{API}/{ep}/purge-queue", key, {})
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
