# FastH3-Omni / MiniMax-H3 (Comfy serverless)

High-quality **still → video** (and optional **audio**) via Comfy on RunPod. Uses the same API shape as [huchukato/runpod-minimax-h3](https://github.com/huchukato/runpod-minimax-h3).

**FastH3-Omni GGUF** ([realrebelai/FastH3-Omni_GGUFs](https://huggingface.co/realrebelai/FastH3-Omni_GGUFs)) is an **optional** diffusion checkpoint inside Comfy — swap into the official **FastH3 Omni / Ref2VA** workflow after the base worker runs. This batch script uses **Director-Storyboard** (one storyboard still + motion prompt), which matches Sweetville **full_visual** best.

## License

**Stop** until you read [`LICENSE_NOTICE.md`](LICENSE_NOTICE.md) and set `ACCEPT_MINIMAX_H3_LICENSE=1`.

## RunPod deploy (summary)

1. **Volume:** ≥160GB, mount at `/runpod-volume` (models download on first boot for official worker).
2. **GPU:** **96GB** class (`BLACKWELL_96` / H100 pool per upstream README).
3. **Hub / image:** Deploy [runpod-minimax-h3](https://github.com/huchukato/runpod-minimax-h3) as **Serverless**; max workers **1** recommended (cold start).
4. Copy **endpoint id** → `FASTH3_ENDPOINT` in `keys.env`.

Optional GGUF: place `FastH3-OmniRef-Unpruned-Q4_K_M.gguf` (or ConvRot safetensors) under Comfy `diffusion_models/` / GGUF loader path and switch workflow checkpoint — **not** automated by this script.

## Config

```bash
cp config.example.env config.env   # gitignored locally
# edit FASTH3_ENDPOINT, paths
source config.env
export ACCEPT_MINIMAX_H3_LICENSE=1
export RUNPOD_API_KEY=...
```

## Batch (full_visual 01–56)

```bash
cd /Users/ujwaltheja/AI/VideoGen/pipelines/fasth3-omni
python3 run_full_visual.py
python3 run_full_visual.py --start 0 --limit 2 --seconds 5
python3 run_full_visual.py --health
```

Output default: `…/clips_from_full_visual_fasth3/` under the series folder.

## Input schema (per job)

Matches Hub README:

- `workflow`: `MiniMaxH3-Director-Storyboard.json`
- `images`: `[cast_master_sheet, full_visual still]` as `data:image/jpeg;base64,…`
- `prompt`: one line motion (from `PROMPTS` / markdown)
- `global_prompt`: Sweetville style block
- `seconds`, `enhance`, `video_size`, `upscale`, `rife`

## vs VideoGen root (Wan TI2V-5B)

| | Wan TI2V-5B pod | FastH3 |
|--|-----------------|--------|
| GPU | 24GB 4090 | 96GB |
| API | `image_b64`, `preset`, `seconds` | Comfy `workflow` + `images[]` |
| License | Apache-2.0 | MiniMax H3 Community |
