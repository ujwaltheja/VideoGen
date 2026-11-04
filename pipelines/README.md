# VideoGen pipelines (new builds)

Two **separate** RunPod/Comfy stacks for Sweetville **full_visual** clips. They do **not** replace the default Hub image (`handler.py` + Wan 2.2 TI2V-5B).

| Pipeline | Model | RunPod shape | Folder |
|----------|--------|--------------|--------|
| **FastH3-Omni** | MiniMax-H3 / FastVideo FastH3 Omni (Comfy) | Serverless **Comfy worker** ([runpod-minimax-h3](https://github.com/huchukato/runpod-minimax-h3)) + optional [FastH3-Omni GGUF](https://huggingface.co/realrebelai/FastH3-Omni_GGUFs) | [`fasth3-omni/`](fasth3-omni/) |
| **LTX-2.5 Dev** | LTX-2.5 22B I2V + optional [rzgar LoRA](https://huggingface.co/rzgar/ltx-2.5-22b-distilled-lora-450-enhanced-n4w) | Serverless **worker-comfyui** + network volume | [`ltx-2.5/`](ltx-2.5/) |

## Shared assets (on your Mac)

- Stills: `~/AI/Main/Kids/series/S01E01_diwali_laddoo_tower/stills_v3_cinematic/full_visual/*.jpg`
- Motion lines: `~/AI/Main/Kids/series/full_visual_prompts/` or `run_minimax_full_visual_base64.PROMPTS`
- Cast sheet: `~/AI/Main/Kids/series/_bible/cast_master_sheet.jpg`
- Output: `…/clips_from_full_visual/` (or per-pipeline subfolders)

## Before you run FastH3

1. Read [`fasth3-omni/LICENSE_NOTICE.md`](fasth3-omni/LICENSE_NOTICE.md) (MiniMax H3 Community License — **territory and commercial terms**).
2. `export ACCEPT_MINIMAX_H3_LICENSE=1` after you accept.
3. Deploy serverless from Hub/worker repo; set `FASTH3_ENDPOINT` in `keys.env`.

## Before you run LTX-2.5

1. Create a **≥160GB** network volume; run [`ltx-2.5/populate-volume.sh`](ltx-2.5/populate-volume.sh) on a pod (or manually).
2. Deploy **worker-comfyui** (or custom image) with LTX-2.5 I2V template; set `LTX_ENDPOINT`.
3. Add **rzgar LoRA** only after base I2V works; strength **0.55–0.65** on **Dev int8-convrot** (see LoRA README).

Legacy Wan 2.2 TI2V-5B worker remains in the repo root (`Dockerfile`, `handler.py`).
