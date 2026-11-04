# MiniMax H3 / FastH3 — license notice (required reading)

**FastH3-Omni** weights (including community GGUFs such as [realrebelai/FastH3-Omni_GGUFs](https://huggingface.co/realrebelai/FastH3-Omni_GGUFs)) are **derivatives of MiniMax-H3**. They are **not** Apache-2.0 like Wan 2.2 TI2V-5B.

## What you must do

1. Read the **MiniMax H3 Community License Agreement** shipped with the official weights / [MiniMax](https://www.minimax.io/) release.
2. Confirm **territory and use** rules apply to you (the HF card states the agreement **excludes** certain regions, including **United States, European Union, United Kingdom, and Republic of Korea** — verify the current text in the license PDF).
3. Keep **`LICENSE`** and **`NOTICE`** files with any redistribution, as required by Section III of that agreement.
4. Do **not** deploy FastH3 in production for the kids series until **you** (not this repo) confirm commercial / geographic compliance.

## This repository

Scripts under `pipelines/fasth3-omni/` **do not grant a license**. They only automate API calls **after** you set:

```bash
export ACCEPT_MINIMAX_H3_LICENSE=1
```

That flag means **you** accepted responsibility for compliance.

## Unofficial quantizations

Community repos (Rebel AI GGUF, etc.) are **unofficial**. Verify ComfyUI loader compatibility and quality vs BF16 before batching 56 clips.
