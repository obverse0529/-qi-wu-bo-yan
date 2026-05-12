#!/usr/bin/env python3
"""
抓取 Met Museum 开放数据并转换为 preference 格式

使用 Met Museum API 抓取中国文物数据
"""

import requests
import json
import logging
from typing import List, Dict, Any
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Met Museum API 基础地址
MET_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"


def search_chinese_artifacts(limit: int = 100) -> List[int]:
    """搜索中国文物，返回 objectID 列表"""
    object_ids = []

    # 搜索多个类别
    queries = [
        "chinese+bronze",
        "chinese+ceramic",
        "chinese+porcelain",
        "chinese+jade",
        "chinese+painting",
        "chinese+sculpture",
        "chinese+textile",
    ]

    for query in queries:
        url = f"{MET_API_BASE}/search?q={query}&hasImages=true"

        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                object_ids.extend(data.get("objectIDs", []))
                logger.info(f"查询 '{query}': 获取 {len(data.get('objectIDs', []))} 个ID")
                time.sleep(0.5)  # 避免请求过快
        except Exception as e:
            logger.warning(f"搜索失败 {query}: {e}")

    # 去重
    object_ids = list(set(object_ids))
    logger.info(f"总共获取 {len(object_ids)} 个唯一 objectID")
    return object_ids


def fetch_object_details(object_id: int) -> Dict[str, Any]:
    """获取单个文物的详细信息"""
    url = f"{MET_API_BASE}/objects/{object_id}"

    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning(f"获取详情失败 {object_id}: {e}")

    return None


def fetch_batch(object_ids: List[int], batch_size: int = 50) -> List[Dict[str, Any]]:
    """批量获取文物详情"""
    artifacts = []

    for i in range(0, len(object_ids), batch_size):
        batch = object_ids[i:i + batch_size]
        logger.info(f"获取批次 {i // batch_size + 1}: {len(batch)} 个文物")

        for obj_id in batch:
            details = fetch_object_details(obj_id)
            if details:
                artifacts.append(details)
            time.sleep(0.2)  # 避免请求过快

    return artifacts


def extract_chinese_artifacts(artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """筛选出中国相关的文物"""
    chinese_artifacts = []

    for art in artifacts:
        culture = art.get("culture", "") or ""
        period = art.get("period", "") or ""
        title = art.get("title", "") or ""
        department = art.get("department", "") or ""

        # 判断是否为中国文物
        is_chinese = (
            "China" in culture or
            "Chinese" in culture or
            "Tang" in period or
            "Song" in period or
            "Ming" in period or
            "Qing" in period or
            "Han" in period or
            "Shang" in period or
            "Zhou" in period or
            ("Chinese" in title and "Chinese" in department)
        )

        if is_chinese:
            chinese_artifacts.append({
                "object_id": art.get("objectID"),
                "title": art.get("title", "Unknown"),
                "culture": culture,
                "period": period,
                "dynasty": extract_dynasty(period),
                "medium": art.get("medium", ""),
                "classification": art.get("classification", ""),
                "artist": art.get("artistDisplayName", ""),
                "object_date": art.get("objectDate", ""),
                "description": art.get("objectName", ""),
                "primary_image": art.get("primaryImage", ""),
                "is_public_domain": art.get("isPublicDomain", False),
            })

    logger.info(f"筛选出 {len(chinese_artifacts)} 件中国文物")
    return chinese_artifacts


def extract_dynasty(period: str) -> str:
    """从 period 提取朝代"""
    dynasties = [
        ("Shang", "商"),
        ("Zhou", "周"),
        ("Han", "汉"),
        ("Tang", "唐"),
        ("Song", "宋"),
        ("Ming", "明"),
        ("Qing", "清"),
        ("Yuan", "元"),
        ("Sui", "隋"),
        ("Wei", "魏"),
        ("Jin", "晋"),
        ("Ming", "明"),
        ("Qin", "秦"),
        ("Xia", "夏"),
        ("Shang", "商"),
    ]

    period = period or ""
    for eng, chn in dynasties:
        if eng in period:
            return chn

    return "未知"


def generate_multi_source_descriptions(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """
    为单个文物生成多源描述（模拟不同来源）
    用于构建 preference 数据
    """
    title = artifact.get("title", "未知文物")
    dynasty = artifact.get("dynasty", "未知")
    period = artifact.get("period", "")
    medium = artifact.get("medium", "")
    classification = artifact.get("classification", "")
    description = artifact.get("description", "")
    artist = artifact.get("artist", "")

    # 来源1: 博物馆官方风格（学术详细）
    academic_desc = f"{title}是{period}{classification}，{medium}材质。"

    if artist:
        academic_desc += f"作者：{artist}。"

    if description:
        academic_desc += f"器物描述：{description}。"

    academic_desc += f"该文物对于研究{period}时期的社会文化具有重要价值。"

    # 来源2: 通俗讲解风格（生动易懂）
    popular_desc = f"{title}"

    if dynasty != "未知":
        popular_desc += f"，{dynasty}代"

    if classification:
        popular_desc += f"的{classification}"

    popular_desc += "，"

    if medium:
        popular_desc += f"以{medium}制成，"

    if description:
        popular_desc += f"特点是{description}。"

    popular_desc += f"这件文物展现了古代工匠的高超技艺。"

    # 来源3: 简略百科风格（简短）
    brief_desc = f"{title}，{period}。"

    if medium:
        brief_desc += f"{medium}质地。"

    return {
        "artifact_id": f"met_{artifact.get('object_id', '')}",
        "artifact_name": title,
        "dynasty": dynasty,
        "category": classification,
        "descriptions": [
            {
                "source": "Met Museum 学术资料",
                "content": academic_desc,
                "style": "学术详细",
                "detail_level": "高",
                "quality_rank": 3,
            },
            {
                "source": "博物馆讲解员版本",
                "content": popular_desc,
                "style": "通俗生动",
                "detail_level": "中",
                "quality_rank": 2,
            },
            {
                "source": "百科简略版",
                "content": brief_desc,
                "style": "简略",
                "detail_level": "低",
                "quality_rank": 1,
            },
        ],
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="抓取 Met Museum 中国文物数据")
    parser.add_argument("--limit", type=int, default=200, help="抓取文物数量")
    parser.add_argument("--output", type=str, default="dataset/annotations/preferences/met_museum_raw.jsonl", help="输出路径")
    args = parser.parse_args()

    # 1. 搜索中国文物
    logger.info("搜索 Met Museum 中国文物...")
    object_ids = search_chinese_artifacts(limit=args.limit)

    # 2. 批量获取详情
    logger.info("获取文物详情...")
    artifacts = fetch_batch(object_ids[:args.limit])

    # 3. 筛选中国文物
    logger.info("筛选中国文物...")
    chinese_artifacts = extract_chinese_artifacts(artifacts)

    # 4. 生成多源描述
    logger.info("生成多源描述...")
    preference_data = []
    for art in chinese_artifacts:
        pref = generate_multi_source_descriptions(art)
        preference_data.append(pref)

    # 5. 保存
    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    with open(args.output, 'w', encoding='utf-8') as f:
        for item in preference_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    logger.info(f"已保存 {len(preference_data)} 条偏好数据到: {args.output}")

    # 6. 同时保存原始数据
    raw_output = args.output.replace(".jsonl", "_raw.jsonl")
    with open(raw_output, 'w', encoding='utf-8') as f:
        for art in chinese_artifacts:
            f.write(json.dumps(art, ensure_ascii=False) + '\n')

    logger.info(f"原始数据已保存到: {raw_output}")

    return preference_data


if __name__ == "__main__":
    main()
