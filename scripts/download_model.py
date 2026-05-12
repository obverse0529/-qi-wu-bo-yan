#!/usr/bin/env python3
"""
下载 Qwen2.5-3B 模型到本地
"""

import os
import sys
from huggingface_hub import snapshot_download

model_dir = "C:/Users/hbusl/qi_wu_bo_yan/models/llm/qwen2.5-3b-hf"

# 清理 incomplete 文件
cache_dir = os.path.join(model_dir, ".cache", "huggingface", "download")
if os.path.exists(cache_dir):
    for f in os.listdir(cache_dir):
        if f.endswith('.incomplete'):
            path = os.path.join(cache_dir, f)
            os.remove(path)
            print(f"Removed incomplete: {f}")

print("Starting Qwen2.5-3B download...")
print(f"Destination: {model_dir}")

try:
    snapshot_download(
        "Qwen/Qwen2.5-3B",
        local_dir=model_dir,
        local_dir_use_symlinks=False,
    )
    print("Download complete!")

    # Verify
    safetensors = [f for f in os.listdir(model_dir) if f.endswith('.safetensors')]
    print(f"Safetensors files: {safetensors}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
