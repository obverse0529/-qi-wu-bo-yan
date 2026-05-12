#!/usr/bin/env python3
"""
将文物数据转换为训练格式 (JSONL)
用于 Gemma QLoRA 微调
"""

import json
import random
from pathlib import Path

def convert_to_training_format(input_file: str, output_dir: str, train_ratio: float = 0.8, val_ratio: float = 0.1):
    """转换数据为训练格式"""

    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        artifacts = json.load(f)

    # 转换为训练样本
    samples = []
    for artifact in artifacts:
        sample = {
            "artifact_id": artifact["artifact_id"],
            "artifact_name": artifact["name"],
            "dynasty": artifact["dynasty"],
            "category": artifact["category"],
            "story": artifact.get("story", ""),
            "source": artifact.get("source", ""),
        }
        samples.append(sample)

    # 打乱顺序
    random.shuffle(samples)

    # 分割数据集
    n = len(samples)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)

    train_samples = samples[:train_end]
    val_samples = samples[train_end:val_end]
    test_samples = samples[val_end:]

    # 写入文件
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for split_name, split_data in [("train", train_samples), ("val", val_samples), ("test", test_samples)]:
        output_file = output_path / f"{split_name}.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for sample in split_data:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        print(f"写入 {output_file}: {len(split_data)} 条样本")

    print(f"\n总计: {n} 条样本")
    print(f"训练集: {len(train_samples)} 条")
    print(f"验证集: {len(val_samples)} 条")
    print(f"测试集: {len(test_samples)} 条")

if __name__ == "__main__":
    import sys
    project_root = Path(__file__).parent.parent
    input_file = project_root / "dataset" / "sample_artifacts.json"
    output_dir = project_root / "dataset" / "annotations" / "stories"

    convert_to_training_format(str(input_file), str(output_dir))
