[![Runpod](https://api.runpod.io/badge/ujwaltheja/VideoGen)](https://console.runpod.io/hub/listing/ujwaltheja/VideoGen)

# Kids clips — Runpod serverless

Image-to-video for Tiny Tales (Milo, Rosie, Ollie). Send a still from ImageGen and a short motion line. The worker keeps the faces and outfits locked to that picture.

`handler.py` is a queue-based [handler function](https://docs.runpod.io/serverless/overview#handler-functions): it reads `event["input"]`, returns a dict, and starts with `runpod.serverless.start({"handler": handler})`.

## Model

**Wan 2.2 TI2V-5B** (`Wan-AI/Wan2.2-TI2V-5B-Diffusers`).

| | |
|---|---|
| Why this one | Fastest open Apache-2.0 model that takes a still and draws a new 720P clip on a 4090. Same licence call as Klein 4B: a monetised kids channel can use it. |
| Not used | Wan 2.2 I2V A14B. Better per-frame quality, two 14B experts, needs 48 GB+ or heavy offload. LTX-2.3 is quicker but not Apache-2.0. |
| Speed | UniPC, 8 steps, UMT5 on CPU, transformer on the GPU. On a warm RTX 4090 a draft 832×480 clip is tens of seconds. Landscape 1280×704 is about a minute. |
| Motion | The still is the first frame. The prompt only asks for gentle life. `lock` is baked into the text the same way ImageGen locks identity. |

Same GPU class as ImageGen. Draft 832×480 is the ImageGen draft still, which is what Kids Video Studio already sends.

## Deploy

GPU: **RTX 4090** first, then **5090**, then L40S / 6000 Ada / A40. Container disk **80 GB** (the image holds Wan + UMT5). Workers **min 0, max 1**, idle timeout **5 s**, FlashBoot **on**. CUDA **12.8 and 13.x** (not 12.0–12.7). Same supply trap as ImageGen: 4090s with capacity sit on **13.2** hosts today. A 12.8-only list returns supply constraints, then Runpod tries B300 MIG / PRO 4500, which this worker must not use.

In the console GPU list pick **4090 + 5090**. Do not pick B300 MIG, PRO 6000 MIG, or RTX PRO 4500. The Hub listing already encodes that: `ADA_24,ADA_32_PRO,ADA_48_PRO,AMPERE_48` with the MIG ids negated.

```bash
cd ~/AI/VideoGen
docker build -t yourname/tinytales-clips:ti2v5b .
docker push yourname/tinytales-clips:ti2v5b
```

In the RunPod console: Serverless → New endpoint → that image → GPU **4090 and 5090** → CUDA 12.8/13.x → the limits above. Copy the endpoint id. If an old endpoint is stuck on CUDA 12.0–12.8 only, edit it or make a new one. Hub listings need a new GitHub release before this GPU list is what Deploy uses.

```bash
export RUNPOD_API_KEY="..."          # same key as stills / music, never commit it
export VIDEO_EP="the-endpoint-id"
python3 client.py still.jpg "gentle smile, leaves drifting, camera still" out.mp4
python3 client.py --preset draft still.jpg "tiny happy bounce" draft.mp4
python3 client.py --preset short --seconds 5 still.jpg "Ollie blinks, Rosie claps" short.mp4
```

First job after idle is the cold start (container plus loading Wan into GPU memory, often two to four minutes). The next clips on that warm worker are the fast ones. `client.py` purges the queue after the download, same as ImageGen.

Kids Video Studio already speaks this schema (`image_base64`, `length`, `cfg`). Paste the new endpoint id into `runpod.i2v_endpoint` and leave the Hub ComfyUI worker behind.

## Request

`POST https://api.runpod.ai/v2/$VIDEO_EP/run`

```json
{
  "input": {
    "prompt": "gentle smile, leaves drifting, camera still",
    "image_b64": "...",
    "preset": "landscape",
    "steps": 8,
    "seed": -1
  },
  "policy": {"ttl": 900000}
}
```

| Field | Default | Meaning |
|---|---|---|
| `prompt` | required | The motion. The worker adds a short identity lock. |
| `image_b64` | required | JPEG/PNG still. `image_base64` from the studio Hub client also works. |
| `preset` | `landscape` | `landscape` 1280×704 (720P), `short` 704×1280, `draft` 832×480 (fastest, matches ImageGen draft). |
| `width`, `height` | from the preset | Multiples of 32, clamped to 480–1280. If you set either, it overrides that side of the preset. |
| `seconds` | 3.4 (81 frames) | Clip length. Snapped to a 4n+1 frame count at 24 fps, max 5 s (121 frames). Draft defaults to 49 frames. |
| `length` | | Studio/Hub frame count. If the body looks like the Hub worker (`image_base64` + `cfg`), `length` is 16 fps frames and is converted to 24 fps. |
| `steps` | 8 | Clamped to 4–20. Official Wan uses 50; 8 is the fast schedule the studio already uses. |
| `cfg` | 5.0 | Also accepts `guidance_scale` / `cfg_scale`. Studio sends 2.0, which is fine. |
| `negative_prompt` | kids-safe list | Appended to the built-in negative. |
| `seed` | random | `0` or higher repeats a take. |
| `health` | | `{"health": true}` returns without drawing. |

## Response

```json
{
  "video_b64": "...",
  "format": "mp4",
  "width": 1280,
  "height": 704,
  "frames": 81,
  "fps": 24,
  "duration_s": 3.375,
  "seed": 7,
  "steps": 8,
  "guidance": 5.0,
  "gen_s": 42.1,
  "model": "Wan2.2-TI2V-5B"
}
```

`gen_s` is GPU time for that clip, not the cold start. Save with `base64.b64decode` on `video_b64`. The studio client already reads `video_b64` or `video`.

## What you pay

Roughly, a warm 4090 at community rates (~$0.34/hr):

| Clip | GPU time | Cost |
|---|---|---|
| Draft 832×480, ~2 s, 8 steps | ~20–40 s | well under a cent |
| Landscape 1280×704, ~3.4 s, 8 steps | ~45–90 s | about a cent |
| Cold start of about three minutes | | about 1–2 cents |

Draft is the cheap option when you are sketching a shot. Landscape is what you want after ImageGen's 1216×832 still.

## Checks on a laptop

```bash
python3 test_prompt.py
```

That does not load the model. The model runs only inside the worker.
