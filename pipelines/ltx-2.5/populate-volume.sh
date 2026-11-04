#!/usr/bin/env bash
# Download LTX-2.5 Comfy INT8 stack + I2V upscaler onto a RunPod volume.
# Run inside a pod with volume mounted at /runpod-volume and huggingface-cli installed.
set -euo pipefail

ROOT="${VOLUME_ROOT:-/runpod-volume}"
MODELS="$ROOT/models"
REPO="${LTX_REPO:-Lightricks/LTX-2.5}"

mkdir -p "$MODELS"/{diffusion_models,text_encoders,vae,latent_upscale_models,loras}

echo "Downloading LTX-2.5 INT8 ConvRot stack from $REPO → $MODELS"

hf download "$REPO" \
  diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors \
  text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors \
  text_encoders/gemma4_e2b_it_bf16.safetensors \
  vae/ltx-2.5-video-vae-conv-bf16.safetensors \
  vae/ltx-2.5-audio-vae-bf16.safetensors \
  latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors \
  --local-dir "$MODELS/ltx-2.5-pack"

# Flatten into ComfyUI layout (worker-comfyui path map)
install -m 644 "$MODELS/ltx-2.5-pack/diffusion_models/"*.safetensors "$MODELS/diffusion_models/" 2>/dev/null || true
install -m 644 "$MODELS/ltx-2.5-pack/text_encoders/"*.safetensors "$MODELS/text_encoders/" 2>/dev/null || true
install -m 644 "$MODELS/ltx-2.5-pack/vae/"*.safetensors "$MODELS/vae/" 2>/dev/null || true
install -m 644 "$MODELS/ltx-2.5-pack/latent_upscale_models/"*.safetensors "$MODELS/latent_upscale_models/" 2>/dev/null || true

echo "Optional: LTX-2.5 Dev int8 (for rzgar LoRA) — large download"
echo "  hf download $REPO diffusion_models/ltx-2.5-22b-dev-transformer-comfy-int8-convrot.safetensors --local-dir $MODELS/ltx-dev"

echo "Optional: rzgar LoRA (after Dev transformer)"
echo "  hf download rzgar/ltx-2.5-22b-distilled-lora-450-enhanced-n4w \\"
echo "    ltx-2.5-22b-distilled-lora-450-rank_256_n4w.safetensors --local-dir $MODELS/loras"

echo "Done. Symlink or map $MODELS into worker-comfyui ComfyUI model dirs."
