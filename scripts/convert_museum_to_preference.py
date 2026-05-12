#!/usr/bin/env python3
"""
将中国博物馆数据转换为 preference 格式

为每个文物生成3个不同风格/质量的描述：
- 学术详细版（高）
- 通俗生动版（中）
- 简略版（低）
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_museum_data(file_path: str) -> List[Dict[str, Any]]:
    """加载博物馆数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    museums = data.get('museums', [])
    all_artifacts = []

    for museum in museums:
        museum_name = museum.get('name', '')
        artifacts = museum.get('artifacts', [])

        for art in artifacts:
            all_artifacts.append({
                'museum': museum_name,
                **art
            })

    logger.info(f"加载 {len(all_artifacts)} 件文物")
    return all_artifacts


def generate_descriptions(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """为单个文物生成多源描述"""
    name = artifact.get('名称', artifact.get('name', '未知文物'))
    era = artifact.get('时代', artifact.get('era', ''))
    category = artifact.get('分类', artifact.get('category', ''))
    description = artifact.get('描述', artifact.get('description', ''))
    artifact_id = artifact.get('编号', '')

    # 朝代简化
    dynasty_map = {
        '商': '商', '西周': '周', '东周': '周', '春秋': '周', '战国': '周',
        '秦': '秦', '西汉': '汉', '东汉': '汉',
        '唐': '唐', '五代': '五代', '宋': '宋', '元': '元',
        '明': '明', '清': '清', '清乾隆': '清', '清雍正': '清',
        '新': '新', '三国': '三国', '南北朝': '南北朝'
    }
    dynasty = dynasty_map.get(era, era) if era else '未知'

    # 来源1: 学术详细版
    academic = f"{name}是{dynasty}时期的{category}。"
    if era:
        academic += f"时代：{era}。"
    if description:
        academic += f"器物描述：{description}"
    academic += f"该文物是研究{dynasty}时期社会文化的重要实物资料，具有重要的历史价值和艺术价值。"

    # 来源2: 通俗生动版
    popular = f"各位游客好！今天为大家介绍{name}。"
    if dynasty != '未知':
        popular += f"这是{dynasty}时期的{category}。"
    if description:
        popular += f"{description}"
    popular += f"站在这件文物前，我们可以感受到古代工匠的精湛技艺。"

    # 来源3: 简略版
    brief = f"{name}，{era}{category}。"
    if description:
        brief += f"{description[:50]}..." if len(description) > 50 else f"{description}"

    # 朝代年份映射（用于学术描述）
    era_years = {
        '商': '约公元前1600-前1046年', '西周': '公元前1046-前771年',
        '春秋': '公元前770-前476年', '战国': '公元前475-前221年',
        '秦': '公元前221-前207年', '西汉': '公元前202年-公元8年',
        '东汉': '公元25-220年', '唐': '公元618-907年',
        '宋': '公元960-1279年', '元': '公元1271-1368年',
        '明': '公元1368-1644年', '清': '公元1644-1911年',
    }

    # 来源4: 带历史背景的详细版（最高质量）
    detailed = academic
    if era in era_years:
        detailed = f"{name}（{era}，{era_years.get(era, '')}）是{dynasty}时期的重要{category}。"
    else:
        detailed = f"{name}是{dynasty}时期的{category}。"
    if description:
        detailed += f"\n\n器物特征：{description}"
    detailed += f"\n\n该文物对于研究{dynasty}时期的手工业发展、社会风俗和文化交流具有重要意义。"

    return {
        'artifact_id': f"museum_{artifact_id}" if artifact_id else name,
        'artifact_name': name,
        'dynasty': dynasty,
        'category': category,
        'era': era,
        'descriptions': [
            {
                'source': f'{artifact.get("museum", "博物馆")}官方资料',
                'content': detailed,
                'style': '学术详细',
                'detail_level': '高',
                'quality_rank': 4,
            },
            {
                'source': '博物馆讲解员版本',
                'content': popular,
                'style': '通俗生动',
                'detail_level': '中',
                'quality_rank': 3,
            },
            {
                'source': '博物馆官方简介',
                'content': academic,
                'style': '简明扼要',
                'detail_level': '中低',
                'quality_rank': 2,
            },
            {
                'source': '百科简略版',
                'content': brief,
                'style': '简略',
                'detail_level': '低',
                'quality_rank': 1,
            },
        ]
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="转换博物馆数据为 preference 格式")
    parser.add_argument("--input", type=str, default="dataset/museum_relics.json")
    parser.add_argument("--output", type=str, default="dataset/annotations/preferences/museum_preference.jsonl")
    args = parser.parse_args()

    # 加载数据
    artifacts = load_museum_data(args.input)

    # 生成多源描述
    preference_data = []
    for art in artifacts:
        pref = generate_descriptions(art)
        preference_data.append(pref)

    # 保存
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        for item in preference_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    logger.info(f"已保存 {len(preference_data)} 条 preference 数据到: {args.output}")

    # 同时保存到 preferences 目录
    final_output = "dataset/annotations/preferences/museum_raw.jsonl"
    with open(final_output, 'w', encoding='utf-8') as f:
        for item in preference_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    logger.info(f"同时保存到: {final_output}")


if __name__ == "__main__":
    main()
