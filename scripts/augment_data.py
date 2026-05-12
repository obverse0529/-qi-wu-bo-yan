#!/usr/bin/env python3
"""
文物故事数据增强脚本
通过同义词替换、句式变化、添加背景信息等方式扩充训练数据
"""

import json
import random
import re
from pathlib import Path

# 朝代信息扩展
DYNASTY_INFO = {
    "商": {"capital": "安阳", "period": "公元前1600-前1046年", "major_events": ["武王伐纣", "盘庚迁殷", "妇好征伐"]},
    "周": {"capital": "镐京/洛邑", "period": "公元前1046-前256年", "major_events": ["武王伐纣", "周公制礼", "春秋战国"]},
    "汉": {"capital": "长安/洛阳", "period": "公元前206年-公元220年", "major_events": ["丝绸之路", "罢黜百家", "文景之治"]},
    "唐": {"capital": "长安", "period": "公元618-907年", "major_events": ["贞观之治", "开元盛世", "安史之乱"]},
    "宋": {"capital": "汴京/临安", "period": "公元960-1279年", "major_events": ["靖康之变", "岳飞抗金", "海上丝绸之路"]},
    "元": {"capital": "大都", "period": "公元1271-1368年", "major_events": ["马可波罗来华", "元曲繁荣"]},
    "明": {"capital": "北京", "period": "公元1368-1644年", "major_events": ["郑和下西洋", "土木堡之变", "资本主义萌芽"]},
    "清": {"capital": "北京", "period": "公元1644-1912年", "major_events": ["康乾盛世", "鸦片战争", "洋务运动"]},
}

# 文物分类信息
CATEGORY_INFO = {
    "青铜器": {"material": "青铜(铜锡铅合金)", "significance": "象征王权与等级", "craft": "泥范法铸造"},
    "陶俑": {"material": "陶器", "significance": "殉葬品，反映生活", "craft": "塑形烧制"},
    "玉器": {"material": "玉石", "significance": "象征美德与权力", "craft": "琢磨雕琢"},
    "瓷器": {"material": "瓷土", "significance": "生活与艺术结合", "craft": "拉坯釉烧"},
    "书画": {"material": "纸绢笔墨", "significance": "艺术与文化传承", "craft": "笔墨勾勒"},
}

# 同义词映射
SYNONYMS = {
    "出土": ["被发掘", "被发现", "出土于", "发掘于"],
    "制作": ["铸造", "烧制", "打造", "制成"],
    "重要": ["珍贵", "宝贵", "意义重大", "极具价值"],
    "历史": ["岁月", "时光", "古代", "往昔"],
    "文化": ["文明", "文化遗产", "精神财富"],
    "研究": ["考证", "探究", "探讨", "分析"],
    "保存": ["保存", "保留", "留存", "完好保存"],
    "发现": ["出土", "出土发现", "被发掘", "重见天日"],
}


def augment_story(story: str, artifact_name: str, dynasty: str, category: str) -> str:
    """增强故事内容"""
    augmented = story

    # 添加朝代背景
    if dynasty in DYNASTY_INFO:
        info = DYNASTY_INFO[dynasty]
        background = f"{dynasty}时期，都城在{info['capital']}，{info['period']}。"
        augmented = background + augmented

    # 添加类别信息
    if category in CATEGORY_INFO:
        cat_info = CATEGORY_INFO[category]
        augmented = f"{artifact_name}是一件{category}，材质为{cat_info['material']}。{augmented}"

    # 同义词替换
    for word, alternatives in SYNONYMS.items():
        if word in augmented and random.random() > 0.5:
            augmented = augmented.replace(word, random.choice(alternatives), 1)

    return augmented


def generate_variant(artifact: dict, variant_id: int) -> dict:
    """生成文物变体"""
    dynasty = artifact.get("dynasty", "")
    category = artifact.get("category", "")
    name = artifact.get("name", "")

    # 创建变体故事
    original_story = artifact.get("story", "")
    augmented_story = augment_story(original_story, name, dynasty, category)

    # 添加变体标注
    if variant_id > 0:
        variant_marker = f"\n\n【说明】本文为{variant_id}号变体，内容基于原始文物描述扩充。"
        augmented_story += variant_marker

    return {
        "artifact_id": f"{artifact['artifact_id']}_v{variant_id}" if variant_id > 0 else artifact["artifact_id"],
        "artifact_name": name,
        "dynasty": dynasty,
        "category": category,
        "story": augmented_story,
        "source": artifact.get("source", ""),
        "description": artifact.get("description", ""),
    }


def create_synthetic_artifact(base: dict, new_id: int, name_suffix: str = "") -> dict:
    """基于现有文物创建合成变体"""
    dynasty = base.get("dynasty", "")
    category = base.get("category", "")

    # 变化文物名称
    prefixes = ["金", "银", "铜", "玉", "陶", "瓷", "石", "铁"]
    suffixes = ["鼎", "尊", "壶", "瓶", "罐", "盘", "杯", "盏"]

    new_name = base.get("name", "文物") + name_suffix if name_suffix else \
               random.choice(prefixes) + base.get("name", "文物")[1:] if len(base.get("name", "文物")) > 1 else base.get("name", "文物") + random.choice(suffixes)

    # 生成变体描述
    descriptions = [
        f"{new_name}造型独特，工艺精湛，是{dynasty}时期{category}的代表作。",
        f"这件{new_name}保存完好，色彩鲜艳，具有重要的历史和艺术价值。",
        f"{new_name}出土于{dynasty}时期的遗址，为研究当时的丧葬习俗提供了珍贵资料。",
    ]

    # 生成变体故事
    if dynasty in DYNASTY_INFO:
        info = DYNASTY_INFO[dynasty]
        story = f"{new_name}是{dynasty}时期的{category}，反映了当时的社会风貌和文化特色。{info['capital']}作为当时的政治文化中心，出土了众多珍贵文物。这件器物的制作工艺体现了{random.choice(['高超的', '精湛的', '先进的'])}技术水平，对研究{dynasty}历史具有重要意义。"
    else:
        story = f"{new_name}是一件珍贵的{dynasty}{category}，其独特的设计和精美的工艺展现了古代匠人的智慧。"

    return {
        "artifact_id": f"synthetic_{new_id:03d}",
        "artifact_name": new_name,
        "dynasty": dynasty,
        "category": category,
        "story": story,
        "source": "合成数据",
        "description": random.choice(descriptions),
    }


def augment_dataset(input_file: str, output_dir: str, target_count: int = 100):
    """扩充数据集到目标数量"""

    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        artifacts = json.load(f)

    print(f"原始数据: {len(artifacts)} 条")

    augmented = list(artifacts)
    variant_count = 0

    # 策略1: 为每个文物生成多个变体
    for artifact in artifacts:
        # 生成2-3个故事变体
        for i in range(2, 4):
            if len(augmented) >= target_count:
                break
            variant = generate_variant(artifact, i)
            augmented.append(variant)
            variant_count += 1

    # 策略2: 生成合成文物
    synthetic_id = 1
    categories_seen = list(set(a.get("category", "") for a in artifacts))
    dynasties_seen = list(set(a.get("dynasty", "") for a in artifacts))

    while len(augmented) < target_count:
        base = random.choice(artifacts)
        synthetic = create_synthetic_artifact(base, synthetic_id)
        augmented.append(synthetic)
        synthetic_id += 1

    print(f"增强后数据: {len(augmented)} 条")
    print(f"  - 原始数据: {len(artifacts)} 条")
    print(f"  - 故事变体: {variant_count} 条")
    print(f"  - 合成数据: {synthetic_id - 1} 条")

    # 分割数据集
    random.shuffle(augmented)
    n = len(augmented)
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)

    train_data = augmented[:train_end]
    val_data = augmented[train_end:val_end]
    test_data = augmented[val_end:]

    # 写入文件
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for split_name, split_data in [("train", train_data), ("val", val_data), ("test", test_data)]:
        output_file = output_path / f"{split_name}.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in split_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        print(f"写入 {output_file}: {len(split_data)} 条样本")

    print(f"\n总计: {n} 条样本")
    return augmented


if __name__ == "__main__":
    import sys

    project_root = Path(__file__).parent.parent
    input_file = project_root / "dataset" / "sample_artifacts.json"
    output_dir = project_root / "dataset" / "annotations" / "stories"

    # 目标: 100条训练数据
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 100

    print(f"开始数据增强，目标: {target} 条\n")
    augment_dataset(str(input_file), str(output_dir), target)
