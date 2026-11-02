"""Prompt, size and frame rules for the kids I2V worker. No torch, so this can be checked on a laptop."""
from __future__ import annotations

import math

# Native TI2V-5B is 24 fps. Frame count must be 4n+1 because of the 4× temporal VAE.
FPS = 24
FRAME_MOD = 4
MIN_FRAMES = 17
MAX_FRAMES = 121
DEFAULT_FRAMES = 81

# Official 720P sizes are 1280×704 / 704×1280. Draft matches ImageGen + the studio I2V frame.
PRESETS = {
    "landscape": (1280, 704),
    "short": (704, 1280),
    "draft": (832, 480),
}
PRESET_AREAS = {name: w * h for name, (w, h) in PRESETS.items()}

# TI2V-5B patchifies 32×32 after the 16× VAE. Sides must be multiples of 32.
SNAP = 32
MIN_SIDE = 480
MAX_SIDE = 1280

DEFAULT_STEPS = 8
MAX_STEPS = 20
DEFAULT_GUIDANCE = 5.0
STUDIO_FPS = 16

LOCK = (
    "Keep every character, face, outfit and object exactly as in the picture — do not redraw anyone. "
    "Add only soft, slow life: a gentle smile, a tiny happy bounce, leaves and clouds drifting slowly, warm sunlight sparkles. "
    "The camera stays still. Hands stay resting and relaxed, arms at the sides, exactly five fingers. "
    "3D preschool cartoon, children safe and happy, fully clothed. "
    "No new people or animals, no walking away, no text, no letters, no logos, no watermark, nothing fast or scary."
)

NEGATIVE = (
    "face morphing, identity change, extra fingers, missing fingers, deformed hands, "
    "walking away, running, fast motion, camera shake, zoom, text, letters, numbers, logo, watermark, "
    "new person, new animal, scary, dark, still picture, blurry, low quality, extra limbs, fused fingers"
)


def snap(n: int, default: int) -> int:
    n = int(n if n else default)
    n = max(MIN_SIDE, min(MAX_SIDE, n))
    return n - (n % SNAP)


def snap_frames(n: int) -> int:
    n = int(n)
    n = max(MIN_FRAMES, min(MAX_FRAMES, n))
    k = round((n - 1) / FRAME_MOD)
    out = int(FRAME_MOD * k + 1)
    return max(MIN_FRAMES, min(MAX_FRAMES, out))


def size_from_area(size: tuple[int, int], max_area: int) -> tuple[int, int]:
    """Keep the still's aspect, cap to the preset area, snap to 32."""
    w, h = int(size[0]), int(size[1])
    aspect = w / max(h, 1)
    height = int(round(math.sqrt(max_area / aspect)))
    width = int(round(height * aspect))
    return snap(width, PRESETS["landscape"][0]), snap(height, PRESETS["landscape"][1])


def resolve_size(width, height, preset: str | None, image_size: tuple[int, int] | None = None) -> tuple[int, int]:
    """Explicit width or height wins. Otherwise the preset. If only a still is given, follow its aspect."""
    preset = (preset or "").strip().lower()
    dw, dh = PRESETS.get(preset, PRESETS["landscape"])
    if width or height:
        return snap(width, dw), snap(height, dh)
    if image_size:
        area = PRESET_AREAS.get(preset, PRESET_AREAS["landscape"])
        return size_from_area(image_size, area)
    return dw, dh


def resolve_frames(data: dict | None, preset: str | None = None) -> int:
    """Seconds win. Studio Hub jobs send `length` as a 16 fps frame count."""
    data = data or {}
    preset = (preset or data.get("preset") or "").strip().lower()
    default = 49 if preset == "draft" else DEFAULT_FRAMES

    if data.get("seconds") not in (None, ""):
        sec = float(data["seconds"])
        return snap_frames(int(round(sec * FPS)))
    if data.get("duration_s") not in (None, ""):
        sec = float(data["duration_s"])
        return snap_frames(int(round(sec * FPS)))
    if data.get("num_frames") not in (None, ""):
        return snap_frames(int(data["num_frames"]))
    if data.get("frames") not in (None, ""):
        return snap_frames(int(data["frames"]))
    if data.get("length") not in (None, ""):
        n = int(data["length"])
        if data.get("fps") not in (None, ""):
            sec = n / max(1.0, float(data["fps"]))
            return snap_frames(int(round(sec * FPS)))
        # Kids Video Studio / Hub worker: length is frames at 16 fps, no fps field.
        if "image_base64" in data or "cfg" in data:
            sec = n / float(STUDIO_FPS)
            return snap_frames(int(round(sec * FPS)))
        return snap_frames(n)
    return default


def clamp_steps(steps) -> int:
    if steps is None or steps == "":
        return DEFAULT_STEPS
    return max(4, min(MAX_STEPS, int(steps)))


def clamp_guidance(value) -> float:
    if value is None or value == "":
        return DEFAULT_GUIDANCE
    return max(1.0, min(8.0, float(value)))


def flow_shift(width: int, height: int) -> float:
    """Wan: 5.0 at 720P, 3.0 at 480P."""
    return 3.0 if max(int(width), int(height)) <= 832 else 5.0


def build_prompt(scene: str) -> str:
    """Motion first, short identity lock after. UMT5 is capped at 512 tokens."""
    scene = " ".join((scene or "").split())
    if not scene:
        raise ValueError("prompt is required")
    if len(scene) > 900:
        scene = scene[:900].rsplit(" ", 1)[0]
    return f"{scene} {LOCK}"


def build_negative(extra: str | None = None) -> str:
    extra = " ".join((extra or "").split())
    return f"{NEGATIVE}, {extra}" if extra else NEGATIVE
