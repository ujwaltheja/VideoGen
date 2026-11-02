"""RunPod serverless image-to-video for Tiny Tales.

Model: Wan 2.2 TI2V-5B (Apache-2.0). One still in, a short clip out.
Fits a 4090 with the UMT5 text encoder on CPU. Warm draft clips are tens of seconds.
"""
from __future__ import annotations

import base64
import io
import os
import random
import tempfile
import time
from pathlib import Path

import runpod
import torch
from PIL import Image

from prompt_build import (
    DEFAULT_STEPS,
    FPS,
    LOCK,
    build_negative,
    build_prompt,
    clamp_guidance,
    clamp_steps,
    flow_shift,
    resolve_frames,
    resolve_size,
)

MODEL_ID = os.environ.get("MODEL_ID", "Wan-AI/Wan2.2-TI2V-5B-Diffusers")
OFFLOAD = os.environ.get("OFFLOAD", "t5").strip().lower()

pipe = None


def load_pipeline() -> None:
    global pipe
    if pipe is not None:
        return
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.benchmark = True
    from diffusers import AutoencoderKLWan, UniPCMultistepScheduler, WanImageToVideoPipeline

    vae = AutoencoderKLWan.from_pretrained(MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanImageToVideoPipeline.from_pretrained(MODEL_ID, vae=vae, torch_dtype=torch.bfloat16)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config, flow_shift=5.0)
    pipe.set_progress_bar_config(disable=True)
    if OFFLOAD == "full":
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")
        # UMT5-XXL is ~11 GB. Keep it on CPU so the 5B transformer has the 24 GB card.
        if OFFLOAD == "t5" and getattr(pipe, "text_encoder", None) is not None:
            pipe.text_encoder.to("cpu")
    if os.environ.get("WARMUP", "1") == "1":
        still = Image.new("RGB", (832, 480), (80, 160, 90))
        _generate(
            still,
            "Milo, Ollie and Rosie stand on green grass under a blue sky, a tiny happy bounce",
            832,
            480,
            frames=17,
            seed=0,
            steps=4,
            guidance=1.0,
            negative=build_negative(),
        )
        torch.cuda.synchronize()


def _set_shift(shift: float) -> None:
    current = float(getattr(pipe.scheduler.config, "flow_shift", 5.0) or 5.0)
    if abs(current - shift) < 1e-6:
        return
    from diffusers import UniPCMultistepScheduler

    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config, flow_shift=shift)


def _fit_image(image: Image.Image, width: int, height: int) -> Image.Image:
    if image.size == (width, height):
        return image
    scale = max(width / image.width, height / image.height)
    nw = max(width, int(round(image.width * scale)))
    nh = max(height, int(round(image.height * scale)))
    image = image.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - width) // 2)
    top = max(0, (nh - height) // 2)
    return image.crop((left, top, left + width, top + height))


def _decode_image(input_data: dict) -> Image.Image:
    raw = input_data.get("image_b64") or input_data.get("image_base64") or input_data.get("image")
    if not raw or not isinstance(raw, str):
        raise ValueError("image_b64 is required")
    if raw.startswith(("http://", "https://", "/")):
        raise ValueError("send the still as image_b64, not a path or URL")
    if raw.startswith("data:"):
        raw = raw.split(",", 1)[1]
    blob = base64.b64decode(raw)
    return Image.open(io.BytesIO(blob)).convert("RGB")


def _generate(
    still: Image.Image,
    scene: str,
    width: int,
    height: int,
    frames: int,
    seed: int,
    steps: int,
    guidance: float,
    negative: str,
) -> list:
    prompt = build_prompt(scene)
    image = _fit_image(still, width, height)
    _set_shift(flow_shift(width, height))
    generator = torch.Generator(device="cuda").manual_seed(seed)
    with torch.inference_mode():
        out = pipe(
            prompt=prompt,
            negative_prompt=negative,
            image=image,
            width=width,
            height=height,
            num_frames=frames,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=generator,
        )
    return out.frames[0]


def _mp4_b64(frames, fps: int) -> str:
    from diffusers.utils import export_to_video

    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        export_to_video(frames, path, fps=fps)
        return base64.b64encode(Path(path).read_bytes()).decode()
    finally:
        Path(path).unlink(missing_ok=True)


def process_data(input_data: dict) -> dict:
    """One clip. Runpod stores this dict as the job output."""
    if input_data.get("health"):
        return {
            "ok": True,
            "model": "Wan2.2-TI2V-5B",
            "fps": FPS,
            "steps": DEFAULT_STEPS,
            "lock_line": LOCK[:80],
        }
    scene = str(input_data.get("prompt") or "").strip()
    if not scene:
        return {"error": "prompt is required"}
    try:
        still = _decode_image(input_data)
    except (ValueError, OSError) as e:
        return {"error": str(e)}
    width, height = resolve_size(
        input_data.get("width"),
        input_data.get("height"),
        input_data.get("preset"),
        still.size,
    )
    frames = resolve_frames(input_data, input_data.get("preset"))
    steps = clamp_steps(input_data.get("steps"))
    guidance = clamp_guidance(input_data.get("guidance_scale", input_data.get("cfg_scale", input_data.get("cfg"))))
    seed = int(input_data.get("seed", -1))
    if seed < 0:
        seed = random.randint(0, 2**31 - 1)
    negative = build_negative(str(input_data.get("negative_prompt") or ""))
    t0 = time.perf_counter()
    video = _generate(still, scene, width, height, frames, seed, steps, guidance, negative)
    torch.cuda.synchronize()
    payload = _mp4_b64(video, FPS)
    duration_s = round(frames / FPS, 3)
    return {
        "video_b64": payload,
        "format": "mp4",
        "width": width,
        "height": height,
        "frames": frames,
        "fps": FPS,
        "duration_s": duration_s,
        "seed": seed,
        "steps": steps,
        "guidance": guidance,
        "gen_s": round(time.perf_counter() - t0, 3),
        "model": "Wan2.2-TI2V-5B",
    }


def handler(event):
    """Queue-based worker. Runpod calls this once per job.

    https://docs.runpod.io/serverless/overview#handler-functions
    """
    input_data = event["input"]
    return process_data(input_data)


# Load Wan outside the handler so each job does not reload the weights.
load_pipeline()
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
