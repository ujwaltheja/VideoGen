#!/usr/bin/env python3
"""Batch full_visual clips via MiniMax-H3 / FastH3 Comfy serverless worker."""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from check_license import require_acceptance  # noqa: E402

# Import PROMPTS from Kids series (run_minimax guarded with __main__)
SERIES = Path(os.environ.get("SERIES_DIR", "/Users/ujwaltheja/AI/Main/Kids/series"))
sys.path.insert(0, str(SERIES))
from run_minimax_full_visual_base64 import BASE, GLOBAL, PROMPTS  # noqa: E402

API = "https://api.runpod.ai/v2"
DEFAULT_EP = os.environ.get("FASTH3_ENDPOINT", "")

NEG = "text, letters, logos, watermark, realistic fur, firecrackers, blurry, low quality"


def _headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "curl/8.0",
    }


def _post(url: str, key: str, body: dict, timeout: float = 120) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers=_headers(key))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _get(url: str, key: str, timeout: float = 120) -> dict:
    req = urllib.request.Request(url, method="GET", headers=_headers(key))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def run_and_wait(ep: str, key: str, inp: dict, max_wait_s: int = 3600, poll_s: int = 15) -> dict:
    job = _post(f"{API}/{ep}/run", key, {"input": inp, "policy": {"ttl": 900_000}})["id"]
    print(f"  job {job}", flush=True)
    t0 = time.time()
    while time.time() - t0 < max_wait_s:
        st = _get(f"{API}/{ep}/status/{job}", key)
        status = st.get("status")
        if status == "COMPLETED":
            return st
        if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
            raise RuntimeError(str(st.get("error") or st.get("output") or st)[:1500])
        time.sleep(poll_s)
    raise TimeoutError(job)


def data_url(path: Path) -> str:
    tmp = Path(tempfile.mktemp(suffix=".jpg"))
    try:
        subprocess.run(
            ["sips", "-s", "format", "jpeg", "-Z", "1280", str(path), "--out", str(tmp)],
            check=True,
            capture_output=True,
        )
        raw = tmp.read_bytes()
    finally:
        tmp.unlink(missing_ok=True)
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def save_outputs(data: dict, out: Path) -> None:
    o = data.get("output") or {}
    outputs = o.get("outputs") or []
    for item in outputs:
        b64 = item.get("b64")
        if not b64:
            continue
        name = (item.get("filename") or "").lower()
        if name.endswith((".mp4", ".webm")) or len(b64) > 100_000:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(base64.b64decode(b64))
            return
    raise RuntimeError(f"no video in outputs: {str(o)[:500]}")


def build_input(
    scene: Path,
    motion: str,
    *,
    workflow: str,
    seconds: int,
    video_size: str,
    cast: Path,
) -> dict:
    images = []
    if cast.is_file():
        images.append(data_url(cast))
    images.append(data_url(scene))
    return {
        "workflow": workflow,
        "prompt": motion,
        "global_prompt": GLOBAL,
        "seconds": seconds,
        "images": images,
        "enhance": True,
        "video_size": video_size,
        "upscale": True,
        "rife": True,
        "overall_soundscape": "soft festive ambience only, no dialogue, no lyrics",
        "non_diegetic_music": "",
    }


def main() -> int:
    require_acceptance()
    p = argparse.ArgumentParser()
    p.add_argument("--endpoint", default=DEFAULT_EP)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--seconds", type=int, default=int(os.environ.get("SECONDS", "5")))
    p.add_argument("--workflow", default=os.environ.get("WORKFLOW", "MiniMaxH3-Director-Storyboard.json"))
    p.add_argument("--video-size", default=os.environ.get("VIDEO_SIZE", "1344x768 (16:9)"))
    p.add_argument("--health", action="store_true")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    ep = args.endpoint.strip()
    if not key or not ep:
        sys.exit("Set RUNPOD_API_KEY and FASTH3_ENDPOINT (or --endpoint)")

    out_dir = SERIES / "S01E01_diwali_laddoo_tower" / os.environ.get("OUT_SUBDIR", "clips_from_full_visual_fasth3")
    cast = SERIES / "_bible/cast_master_sheet.jpg"

    if args.health:
        st = run_and_wait(ep, key, {"action": "health"}, max_wait_s=600, poll_s=10)
        print(json.dumps(st.get("output"), indent=2)[:3000])
        return 0

    files = sorted(BASE.glob("*.jpg"))
    if args.limit > 0:
        files = files[args.start : args.start + args.limit]
    else:
        files = files[args.start :]

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"endpoint={ep} clips={len(files)} → {out_dir}", flush=True)

    ok = fail = skip = 0
    for i, img in enumerate(files):
        out = out_dir / f"{img.stem}.mp4"
        if out.is_file() and not args.force:
            skip += 1
            continue
        motion = PROMPTS.get(img.name, img.stem.replace("_", " "))
        inp = build_input(
            img,
            motion,
            workflow=args.workflow,
            seconds=args.seconds,
            video_size=args.video_size,
            cast=cast,
        )
        print(f"\n[{i + 1}/{len(files)}] {img.name}", flush=True)
        try:
            data = run_and_wait(ep, key, inp)
            save_outputs(data, out)
            print(f"  ok {out.name}", flush=True)
            ok += 1
        except Exception as e:
            print(f"  fail: {e}", flush=True)
            fail += 1
    print(f"done ok={ok} skip={skip} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
