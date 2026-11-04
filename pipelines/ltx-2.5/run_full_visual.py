#!/usr/bin/env python3
"""Batch full_visual via LTX-2.5 I2V on runpod worker-comfyui (exported API workflow)."""
from __future__ import annotations

import argparse
import base64
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

SERIES = Path(os.environ.get("SERIES_DIR", "/Users/ujwaltheja/AI/Main/Kids/series"))
sys.path.insert(0, str(SERIES))
from run_minimax_full_visual_base64 import BASE, PROMPTS  # noqa: E402

ROOT = Path(__file__).resolve().parent
API = "https://api.runpod.ai/v2"
DEFAULT_EP = os.environ.get("LTX_ENDPOINT", "")


def _headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "curl/8.0",
    }


def _post(url: str, key: str, body: dict, timeout: float = 300) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers=_headers(key))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _get(url: str, key: str, timeout: float = 120) -> dict:
    req = urllib.request.Request(url, method="GET", headers=_headers(key))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def run_and_wait(ep: str, key: str, inp: dict, max_wait_s: int = 7200, poll_s: int = 20) -> dict:
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


def compress_jpeg(path: Path, max_px: int = 1280) -> bytes:
    tmp = Path(tempfile.mktemp(suffix=".jpg"))
    try:
        subprocess.run(
            ["sips", "-s", "format", "jpeg", "-Z", str(max_px), str(path), "--out", str(tmp)],
            check=True,
            capture_output=True,
        )
        return tmp.read_bytes()
    finally:
        tmp.unlink(missing_ok=True)


def load_workflow(path: Path) -> dict:
    wf = json.loads(path.read_text(encoding="utf-8"))
    if "nodes" in wf:
        sys.exit(f"{path} is UI format — re-export with Export (API)")
    return wf


def patch_workflow(
    wf: dict,
    *,
    image_node: str,
    prompt_node: str,
    image_name: str,
    prompt: str,
    width: int,
    height: int,
    length: int,
    fps: int,
) -> dict:
    out = copy.deepcopy(wf)
    if image_node not in out:
        sys.exit(f"NODE_LOAD_IMAGE={image_node} not in workflow")
    out[image_node].setdefault("inputs", {})["image"] = image_name
    if prompt_node not in out:
        sys.exit(f"NODE_POSITIVE_PROMPT={prompt_node} not in workflow")
    ins = out[prompt_node].setdefault("inputs", {})
    for key in ("text", "positive", "positive_prompt", "prompt"):
        if key in ins or key in str(out[prompt_node].get("class_type", "")).lower():
            ins[key] = prompt
            break
    else:
        ins["text"] = prompt
    # Best-effort widget patches (template-dependent)
    for nid, node in out.items():
        ct = (node.get("class_type") or "").lower()
        inp = node.setdefault("inputs", {})
        if "emptylatent" in ct or "latent" in ct and "width" in inp:
            inp["width"] = width
            inp["height"] = height
        if "length" in inp and isinstance(inp.get("length"), (int, float)):
            inp["length"] = length
        if "frame_rate" in inp or "fps" in inp:
            if "frame_rate" in inp:
                inp["frame_rate"] = fps
            if "fps" in inp:
                inp["fps"] = fps
    return out


def save_video_from_worker(data: dict, out: Path) -> None:
    o = data.get("output") or {}
    # worker-comfyui: output.images / message / video variants
    for key in ("video", "videos", "images", "gifs"):
        items = o.get(key)
        if not items:
            continue
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("data"):
                    raw = base64.b64decode(item["data"])
                    if raw[:4] == b"\x00\x00\x00\x18" or b"ftyp" in raw[:32]:
                        out.write_bytes(raw)
                        return
                if isinstance(item, str):
                    s = item
                    if s.startswith("data:") and "," in s:
                        s = s.split(",", 1)[1]
                    raw = base64.b64decode(s)
                    out.write_bytes(raw)
                    return
    b64 = o.get("video") or o.get("video_b64")
    if b64:
        s = b64.split(",", 1)[-1] if b64.startswith("data:") else b64
        out.write_bytes(base64.b64decode(s))
        return
    raise RuntimeError(f"no video in output keys={list(o.keys())}")


def motion_prompt(stem: str, jpg: str) -> str:
    motion = PROMPTS.get(jpg, stem.replace("_", " "))
    return (
        f"Use the provided start image as the first frame. {motion} "
        "Soft 3D preschool cartoon, matte vinyl-toy, warm Diwali glow, no dialogue, no text."
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--endpoint", default=DEFAULT_EP)
    p.add_argument("--workflow", default=os.environ.get("WORKFLOW_API_JSON", "workflows/ltx25_i2v_api.json"))
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    ep = args.endpoint.strip()
    if not key or not ep:
        sys.exit("Set RUNPOD_API_KEY and LTX_ENDPOINT")

    wf_path = (ROOT / args.workflow).resolve()
    if not wf_path.is_file():
        sys.exit(
            f"Missing {wf_path}. Export Comfy LTX-2.5 I2V API workflow — see README.md"
        )

    img_node = os.environ.get("NODE_LOAD_IMAGE", "").strip()
    pr_node = os.environ.get("NODE_POSITIVE_PROMPT", "").strip()
    if not img_node or not pr_node:
        sys.exit("Set NODE_LOAD_IMAGE and NODE_POSITIVE_PROMPT in config.env after workflow export")

    width = int(os.environ.get("WIDTH", "768"))
    height = int(os.environ.get("HEIGHT", "512"))
    length = int(os.environ.get("LENGTH", "97"))
    fps = int(os.environ.get("FPS", "24"))

    wf_base = load_workflow(wf_path)
    out_dir = SERIES / "S01E01_diwali_laddoo_tower" / os.environ.get("OUT_SUBDIR", "clips_from_full_visual_ltx25")
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(BASE.glob("*.jpg"))
    if args.limit > 0:
        files = files[args.start : args.start + args.limit]
    else:
        files = files[args.start :]

    print(f"endpoint={ep} clips={len(files)} workflow={wf_path.name}", flush=True)
    ok = fail = skip = 0
    for i, img in enumerate(files):
        out = out_dir / f"{img.stem}.mp4"
        if out.is_file() and not args.force:
            skip += 1
            continue
        prompt = motion_prompt(img.stem, img.name)
        img_bytes = compress_jpeg(img)
        img_name = f"{img.stem}.jpg"
        wf = patch_workflow(
            wf_base,
            image_node=img_node,
            prompt_node=pr_node,
            image_name=img_name,
            prompt=prompt,
            width=width,
            height=height,
            length=length,
            fps=fps,
        )
        body = {
            "input": {
                "workflow": wf,
                "images": [{"name": img_name, "image": base64.standard_b64encode(img_bytes).decode("ascii")}],
            }
        }
        print(f"\n[{i + 1}/{len(files)}] {img.name}", flush=True)
        try:
            data = run_and_wait(ep, key, body["input"])
            save_video_from_worker(data, out)
            print(f"  ok {out.name}", flush=True)
            ok += 1
        except Exception as e:
            print(f"  fail: {e}", flush=True)
            fail += 1
    print(f"done ok={ok} skip={skip} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
