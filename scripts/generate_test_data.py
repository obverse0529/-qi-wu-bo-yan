#!/usr/bin/env python
"""测试数据批量生成工具

Usage:
  python scripts/generate_test_data.py --count 50              # 生成 50 条文物
  python scripts/generate_test_data.py --count 100 --with-stories  # 含故事和任务
  python scripts/generate_test_data.py --clear                # 清空所有测试数据
"""
import argparse
import random
import uuid
from datetime import datetime, timedelta

from faker import Faker

fake = Faker("zh_CN")

DYNASTIES = ["商", "周", "战国", "秦", "汉", "唐", "宋", "元", "明", "清"]
CATEGORIES = ["玉石器", "青铜器", "陶瓷器", "绘画", "珐琅器", "金银器", "漆器", "书法"]
VIEW_TYPES = ["front", "side_left", "side_right", "back", "top", "bottom"]
STORY_TYPES = ["brief", "standard", "detailed"]
RECONSTRUCTION_STATUSES = ["pending", "running", "completed", "failed"]

ARTIFACT_TEMPLATES = [
    {"name": "{dynasty}{material}{category_type}", "dynasty": "唐", "category": "金银器"},
    {"name": "{dynasty}{material}龙纹{category_type}", "dynasty": "明", "category": "陶瓷器"},
    {"name": "{material}雕{theme}纹{category_type}", "dynasty": "清", "category": "玉石器"},
    {"name": "{dynasty}{material}{theme}像", "dynasty": "宋", "category": "绘画"},
]


def generate_artifact():
    """Generate a single artifact record."""
    dynasty = random.choice(DYNASTIES)
    category = random.choice(CATEGORIES)
    materials = random.choice(["玉", "铜", "金", "银", "瓷", "木", "石", "丝"])
    themes = random.choice(["云", "龙", "凤", "花鸟", "山水", "人物", "瑞兽"])

    return {
        "id": str(uuid.uuid4()),
        "name": f"{dynasty}{materials}{themes}纹{category}",
        "dynasty": dynasty,
        "category": category,
        "dimensions": {
            "length": round(random.uniform(5, 120), 1),
            "width": round(random.uniform(3, 80), 1),
            "height": round(random.uniform(2, 60), 1),
            "unit": "cm",
        },
        "description": (
            f"{dynasty}时期的{materials}质{category}，以{themes}纹为主要装饰。"
            f"此器造型优美，工艺精湛，体现了{dynasty}代手工业的最高水平，"
            f"具有重要的历史研究和艺术鉴赏价值。"
        ),
        "metadata": {
            "era": f"{dynasty}代",
            "site": fake.city() + random.choice(["遗址", "墓葬", "宫殿遗址"]),
            "collection": random.choice(["故宫博物院", "国家博物馆", "陕西历史博物馆", "地方博物馆"]),
        },
        "created_at": fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def generate_images(artifact_id: str):
    """Generate 3-6 images for an artifact."""
    images = []
    for view in random.sample(VIEW_TYPES, random.randint(3, 6)):
        w = random.randint(800, 4000)
        h = random.randint(600, 3000)
        images.append({
            "id": str(uuid.uuid4()),
            "artifact_id": artifact_id,
            "view_type": view,
            "image_url": f"https://picsum.photos/{w}/{h}?random={random.randint(1, 9999)}",
            "thumbnail_url": f"https://picsum.photos/200/150?random={random.randint(1, 9999)}",
            "file_path": f"uploads/artifacts/{artifact_id}/{view}.jpg",
            "width": w,
            "height": h,
            "file_size": random.randint(50000, 5000000),
            "created_at": fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
        })
    return images


def generate_model(artifact_id: str):
    """Generate a 3D model record."""
    return {
        "id": str(uuid.uuid4()),
        "artifact_id": artifact_id,
        "model_url": f"https://models.example.com/{artifact_id}.glb",
        "file_path": f"uploads/models/{artifact_id}.glb",
        "polygon_count": random.randint(5000, 100000),
        "has_texture": random.choice([True, True, True, False]),
        "file_size": random.randint(500000, 50000000),
        "status": random.choice(["pending", "completed", "completed", "completed"]),
        "created_at": fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
    }


def generate_story(artifact_id: str):
    """Generate an artifact story."""
    return {
        "id": str(uuid.uuid4()),
        "artifact_id": artifact_id,
        "story_type": random.choice(STORY_TYPES),
        "content": {
            "origin": fake.paragraph(nb_sentences=3),
            "craftsmanship": fake.paragraph(nb_sentences=4),
            "historical_context": fake.paragraph(nb_sentences=3),
            "cultural_significance": fake.paragraph(nb_sentences=3),
            "related_events": [fake.sentence() for _ in range(random.randint(1, 4))],
            "similar_artifacts": [fake.sentence() for _ in range(random.randint(1, 3))],
        },
        "audio_url": None,
        "audio_script": None,
        "created_at": fake.date_time_between(start_date="-6m", end_date="now").isoformat(),
    }


def generate_reconstruction_task(artifact_id: str, model_id: str = None):
    """Generate a reconstruction task record."""
    return {
        "id": str(uuid.uuid4()),
        "artifact_id": artifact_id,
        "status": random.choice(RECONSTRUCTION_STATUSES),
        "progress": random.randint(0, 100),
        "model_id": model_id,
        "error_message": None,
        "started_at": fake.date_time_between(start_date="-30d", end_date="-1d").isoformat(),
        "completed_at": fake.date_time_between(start_date="-1d", end_date="now").isoformat(),
        "created_at": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
    }


def print_sql(count: int, with_stories: bool = False):
    """Print INSERT statements."""
    artifacts = [generate_artifact() for _ in range(count)]

    print("-- ===== 文物基础数据 ({n} 条) =====".format(n=count))
    for a in artifacts:
        print(
            f"INSERT INTO artifacts (id, name, dynasty, category, dimensions, description, metadata, created_at, updated_at) "
            f"VALUES ('{a['id']}', '{a['name']}', '{a['dynasty']}', '{a['category']}', "
            f"'{a['dimensions']}', '{a['description']}', '{a['metadata']}', "
            f"'{a['created_at']}', '{a['updated_at']}');"
        )

    print("\n-- ===== 文物图像 =====")
    for a in artifacts:
        for img in generate_images(a["id"]):
            print(
                f"INSERT INTO artifact_images (id, artifact_id, view_type, image_url, thumbnail_url, file_path, width, height, file_size, created_at) "
                f"VALUES ('{img['id']}', '{img['artifact_id']}', '{img['view_type']}', "
                f"'{img['image_url']}', '{img['thumbnail_url']}', '{img['file_path']}', "
                f"{img['width']}, {img['height']}, {img['file_size']}, '{img['created_at']}');"
            )

    print("\n-- ===== 3D 模型 =====")
    for a in artifacts:
        model = generate_model(a["id"])
        print(
            f"INSERT INTO artifact_models (id, artifact_id, model_url, file_path, polygon_count, has_texture, file_size, status, created_at) "
            f"VALUES ('{model['id']}', '{model['artifact_id']}', '{model['model_url']}', "
            f"'{model['file_path']}', {model['polygon_count']}, {model['has_texture']}, "
            f"{model['file_size']}, '{model['status']}', '{model['created_at']}');"
        )

    if with_stories:
        print("\n-- ===== 文物故事 =====")
        for a in artifacts:
            story = generate_story(a["id"])
            content_str = str(story["content"]).replace("'", "''")
            print(
                f"INSERT INTO artifact_stories (id, artifact_id, story_type, content, created_at) "
                f"VALUES ('{story['id']}', '{story['artifact_id']}', '{story['story_type']}', "
                f"'{content_str}', '{story['created_at']}');"
            )

    print(f"\n-- 共生成 {count} 件文物数据")
    print("-- 使用: psql -U postgres -d qiwu -f <this_file>.sql")


def print_clear_sql():
    """Print DELETE statements."""
    print("-- ===== 清空测试数据 =====")
    print("DELETE FROM artifact_stories;")
    print("DELETE FROM reconstruction_tasks;")
    print("DELETE FROM artifact_models;")
    print("DELETE FROM artifact_images;")
    print("DELETE FROM artifacts;")
    print("-- 数据已清空")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="启物博言测试数据生成工具")
    parser.add_argument("--count", type=int, default=50, help="生成文物数量")
    parser.add_argument("--with-stories", action="store_true", help="同时生成故事数据")
    parser.add_argument("--clear", action="store_true", help="清空所有测试数据")
    args = parser.parse_args()

    if args.clear:
        print_clear_sql()
    else:
        print_sql(args.count, args.with_stories)
