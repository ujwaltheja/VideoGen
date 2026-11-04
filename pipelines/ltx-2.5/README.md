# LTX-2.5 Dev + I2V (Comfy on RunPod)

Open **Lightricks LTX-2.5** image-to-video for Sweetville **full_visual** stills. Optional **[rzgar LoRA](https://huggingface.co/rzgar/ltx-2.5-22b-distilled-lora-450-enhanced-n4w)** stacks on top of the **Dev int8-convrot** transformer (see below).

## License (Lightricks)

LTX-2.x uses the **Lightricks LTX-2.x License**. Entities with **≥ $10M annual revenue** need a **commercial agreement** (`ltxv-licensing@lightricks.com`). Read the full text on [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5). This repo does not legal-review your use.

## Architecture

| Phase | What |
|-------|------|
| **1. Base I2V** | Comfy template `video_ltx2_5_i2v` — distilled **INT8 ConvRot** stack on **L40S / A100** (32GB+ with offload) |
| **2. rzgar LoRA (optional)** | Only after base works. Author targets **LTX-2.5 Dev** `int8-convrot`, **not** distilled — strength **0.55–0.65**, stack with your N54W LoRAs |

Default batch script targets **distilled I2V** (no rzgar). Enable rzgar only in a **Dev** workflow export you maintain locally.

## RunPod setup

1. **Network volume** ≥ **160GB**, mount at `/runpod-volume`.
2. On a one-off pod, run [`populate-volume.sh`](populate-volume.sh) (needs `huggingface-cli` + `HF_TOKEN` for gated files if any).
3. Deploy **[runpod/worker-comfyui](https://github.com/runpod-workers/worker-comfyui)** (or custom image) with:
   - ComfyUI **≥** version that includes LTX-2.5 templates
   - Custom nodes / models path map to volume (`diffusion_models`, `text_encoders`, `vae`, `latent_upscale_models`, `loras`)
4. In ComfyUI: **Templates → LTX-2.5 → Image-to-Video** → **Export (API)** → save as  
   `workflows/ltx25_i2v_api.json` (gitignored — large).
5. Set node IDs in `config.env` (see `config.example.env`) after export.
6. Serverless **endpoint id** → `LTX_ENDPOINT`.

## Config

```bash
cp config.example.env config.env
source config.env
export RUNPOD_API_KEY=...
```

## Batch

```bash
cd /Users/ujwaltheja/AI/VideoGen/pipelines/ltx-2.5
python3 run_full_visual.py --limit 1
python3 run_full_visual.py
```

Output: `…/clips_from_full_visual_ltx25/`

## rzgar LoRA install

After **Dev** transformer is on the volume:

```bash
# Example — pick one rank
hf download rzgar/ltx-2.5-22b-distilled-lora-450-enhanced-n4w \
  ltx-2.5-22b-distilled-lora-450-rank_256_n4w.safetensors \
  --local-dir /runpod-volume/models/loras
```

Wire into your **Dev** workflow LoRA loader nodes; **do not** use with the distilled batch script until you duplicate the workflow for Dev + rzgar.

## Docs

- [LTX I2V guide](https://docs.ltx.io/open-source-model/usage-guides/image-to-video)
- [Comfy integration](https://docs.ltx.io/open-source-model/integration-tools/comfy-ui)
