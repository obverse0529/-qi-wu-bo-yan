#!/usr/bin/env python3
"""
将多源文物数据转换为 DPO 偏好对格式

读取 raw preference 数据（多个来源的描述），输出 DPO 格式的 (chosen, rejected) 对
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_raw_preferences(file_path: str) -> List[Dict[str, Any]]:
    """加载原始偏好数据"""
    samples = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                samples.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    logger.info(f"加载 {len(samples)} 条原始数据: {file_path}")
    return samples


def convert_to_dpo_pairs(sample: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    将单个文物的多源描述转换为多个 (chosen, rejected) 对

    排序逻辑：按 quality_rank 从高到低
    每对 = (quality_rank更高的, quality_rank更低的)
    """
    artifact_name = sample.get("artifact_name", "未知文物")
    dynasty = sample.get("dynasty", "未知")
    category = sample.get("category", "未知")
    artifact_id = sample.get("artifact_id", "")

    descriptions = sample.get("descriptions", [])
    if len(descriptions) < 2:
        return []

    # 按 quality_rank 排序
    sorted_descs = sorted(descriptions, key=lambda x: x.get("quality_rank", 0), reverse=True)

    # 构建 prompt
    prompt = f"""你是一个专业的中国博物馆文物讲解员。请根据以下文物信息，写一段详细的文物介绍。

文物信息：
- 名称：{artifact_name}
- 朝代：{dynasty}
- 分类：{category}

请用生动、专业的语言介绍这件文物，要求内容准确、详实、有深度。"""

    # 生成所有 (chosen, rejected) 对
    pairs = []
    for i in range(len(sorted_descs)):
        for j in range(len(sorted_descs)):
            if i < j:  # chosen 比 rejected 质量高
                pairs.append({
                    "prompt": prompt,
                    "chosen": sorted_descs[i]["content"],
                    "rejected": sorted_descs[j]["content"],
                    "artifact_id": artifact_id,
                    "chosen_source": sorted_descs[i].get("source", ""),
                    "rejected_source": sorted_descs[j].get("source", ""),
                    "chosen_rank": sorted_descs[i].get("quality_rank", 0),
                    "rejected_rank": sorted_descs[j].get("quality_rank", 0),
                })

    return pairs


def main():
    import argparse
    parser = argparse.ArgumentParser(description="转换为 DPO 偏好对格式")
    parser.add_argument("--input-dir", type=str, default="dataset/annotations/preferences", help="原始数据目录")
    parser.add_argument("--output", type=str, default="dataset/annotations/preferences/preferences.jsonl", help="输出文件")
    args = parser.parse_args()

    # 收集所有 raw 文件
    input_dir = Path(args.input_dir)
    raw_files = list(input_dir.glob("*_raw.jsonl"))

    if not raw_files:
        logger.warning(f"未找到 raw 文件: {input_dir}/*_raw.jsonl")
        return

    # 转换所有数据
    all_pairs = []
    for raw_file in raw_files:
        samples = load_raw_preferences(str(raw_file))
        for sample in samples:
            pairs = convert_to_dpo_pairs(sample)
            all_pairs.extend(pairs)

    logger.info(f"生成 {len(all_pairs)} 个偏好对")

    # 保存
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    logger.info(f"已保存到: {args.output}")

    # 统计
    logger.info(f"\n统计:")
    logger.info(f"  - 原始文物数: {len(all_pairs) // 3 if all_pairs else 0}")  # 每个文物约3对
    logger.info(f"  - 偏好对总数: {len(all_pairs)}")


if __name__ == "__main__":
    main()
