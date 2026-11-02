# Weights are baked in so a cold start loads from disk instead of downloading Wan 2.2.
# Base tag is the current RunPod PyTorch 2.9 / CUDA 12.8 image (RTX 4090 and 5090).
FROM runpod/pytorch:1.5.1-rc.175-cu1281-torch291-ubuntu2204

WORKDIR /app

ENV HF_HOME=/opt/hf \
    HF_HUB_CACHE=/opt/hf/hub \
    PYTHONUNBUFFERED=1 \
    MODEL_ID=Wan-AI/Wan2.2-TI2V-5B-Diffusers \
    OFFLOAD=t5 \
    WARMUP=1

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade-strategy only-if-needed -r requirements.txt \
    && python -c "from huggingface_hub import snapshot_download; snapshot_download('Wan-AI/Wan2.2-TI2V-5B-Diffusers')"

COPY prompt_build.py handler.py ./

# Worker must not stall on Hugging Face at request time.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

CMD ["python", "-u", "handler.py"]
