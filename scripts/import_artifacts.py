#!/usr/bin/env python3
"""
文物数据批量导入脚本
用于将整理好的文物数据批量导入数据库

使用方法:
    python scripts/import_artifacts.py --source dataset/artifacts.csv
    python scripts/import_artifacts.py --source dataset/artifacts.json --format json
"""

import argparse
import csv
import json
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.artifact import Artifact, ArtifactImage, ArtifactStory
from app.services.kg_service import get_kg_service
from app.services.rag_service import get_rag_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def import_from_csv(
    file_path: str,
    batch_size: int = 10,
    skip_existing: bool = True,
    kg_service=None,
    rag_service=None,
) -> Dict[str, int]:
    """
    从 CSV 导入文物数据

    CSV 格式:
        artifact_id,name,dynasty,category,site,materials,techniques,description
        artifact_001,青铜鼎,商,青铜器,安阳,青铜,铸造,这是...
    """
    stats = {"total": 0, "imported": 0, "skipped": 0, "errors": 0}

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch = []

        for row in reader:
            stats["total"] += 1
            batch.append(row)

            if len(batch) >= batch_size:
                result = await _import_batch(batch, skip_existing, kg_service, rag_service)
                stats["imported"] += result["imported"]
                stats["skipped"] += result["skipped"]
                stats["errors"] += result["errors"]
                batch = []

        if batch:
            result = await _import_batch(batch, skip_existing, kg_service, rag_service)
            stats["imported"] += result["imported"]
            stats["skipped"] += result["skipped"]
            stats["errors"] += result["errors"]

    return stats


async def import_from_json(
    file_path: str,
    batch_size: int = 10,
    skip_existing: bool = True,
    kg_service=None,
    rag_service=None,
) -> Dict[str, int]:
    """
    从 JSON 导入文物数据

    JSON 格式:
        [
            {
                "artifact_id": "artifact_001",
                "name": "青铜鼎",
                "dynasty": "商",
                "category": "青铜器",
                "site": "安阳",
                "materials": ["青铜"],
                "techniques": ["铸造"],
                "description": "这是...",
                "images": [
                    {"view": "front", "path": "dataset/images/artifact_001_front.png"},
                    ...
                ],
                "story": "这是文物故事...",
                "source": "《文物》2020年第1期"
            },
            ...
        ]
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stats = {"total": len(data), "imported": 0, "skipped": 0, "errors": 0}

    batch = []
    for item in data:
        batch.append(item)
        if len(batch) >= batch_size:
            result = await _import_batch(batch, skip_existing, kg_service, rag_service)
            stats["imported"] += result["imported"]
            stats["skipped"] += result["skipped"]
            stats["errors"] += result["errors"]
            batch = []

    if batch:
        result = await _import_batch(batch, skip_existing, kg_service, rag_service)
        stats["imported"] += result["imported"]
        stats["skipped"] += result["skipped"]
        stats["errors"] += result["errors"]

    return stats


async def _import_batch(
    batch: List[Dict[str, Any]],
    skip_existing: bool,
    kg_service=None,
    rag_service=None,
) -> Dict[str, int]:
    """批量导入一组文物"""
    imported = 0
    skipped = 0
    errors = 0

    async with AsyncSessionLocal() as db:
        for item in batch:
            try:
                result = await _import_single_artifact(
                    db, item, skip_existing, kg_service, rag_service
                )
                if result == "imported":
                    imported += 1
                elif result == "skipped":
                    skipped += 1
            except Exception as e:
                logger.error(f"导入失败 {item.get('artifact_id', 'unknown')}: {e}")
                errors += 1

        await db.commit()

    return {"imported": imported, "skipped": skipped, "errors": errors}


async def _import_single_artifact(
    db: AsyncSession,
    data: Dict[str, Any],
    skip_existing: bool,
    kg_service=None,
    rag_service=None,
) -> str:
    """导入单个文物"""
    artifact_id = data.get("artifact_id")
    if not artifact_id:
        raise ValueError("缺少 artifact_id")

    # 检查是否已存在
    if skip_existing:
        query = select(Artifact).where(Artifact.id == artifact_id)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"跳过已存在: {artifact_id}")
            return "skipped"

    # 创建文物记录
    artifact = Artifact(
        id=artifact_id,
        name=data.get("name", ""),
        dynasty=data.get("dynasty"),
        category=data.get("category"),
        site=data.get("site"),
        materials=",".join(data.get("materials", [])) if isinstance(data.get("materials"), list) else data.get("materials", ""),
        techniques=",".join(data.get("techniques", [])) if isinstance(data.get("techniques"), list) else data.get("techniques", ""),
        description=data.get("description", ""),
        provenance=data.get("provenance", ""),
        era=data.get("era", ""),
    )
    db.add(artifact)

    # 添加图像
    for img_data in data.get("images", []):
        image = ArtifactImage(
            artifact_id=artifact_id,
            view_type=img_data.get("view", "unknown"),
            file_path=img_data.get("path", ""),
            file_url=img_data.get("url", ""),
        )
        db.add(image)

    await db.flush()

    # 同步到知识图谱
    try:
        if kg_service is None:
            kg_service = get_kg_service()
            kg_service.connect()
        kg_service.build_from_artifact_data(
            artifact_id=artifact_id,
            name=data.get("name", ""),
            dynasty=data.get("dynasty", ""),
            category=data.get("category", ""),
            site=data.get("site"),
            techniques=data.get("techniques", []),
            materials=data.get("materials", []),
        )
    except Exception as e:
        logger.warning(f"知识图谱同步失败: {e}")

    # 添加到 RAG 向量库
    story = data.get("story")
    if story:
        try:
            if rag_service is None:
                rag_service = get_rag_service()
                rag_service.connect()
            rag_service.add_document(
                artifact_id=artifact_id,
                artifact_name=data.get("name", ""),
                content=story,
                source=data.get("source", ""),
                source_type="artifact_story",
            )
        except Exception as e:
            logger.warning(f"RAG 添加失败: {e}")

    logger.info(f"导入成功: {artifact_id}")
    return "imported"


async def check_import_status(file_path: str) -> Dict[str, Any]:
    """检查导入状态"""
    stats = {"total": 0, "in_db": 0, "missing_images": 0}

    if file_path.endswith('.csv'):
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            stats["total"] = len(rows)
    elif file_path.endswith('.json'):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            stats["total"] = len(data)

    async with AsyncSessionLocal() as db:
        query = select(Artifact)
        result = await db.execute(query)
        artifacts = result.scalars().all()
        stats["in_db"] = len(artifacts)

        for artifact in artifacts:
            img_query = select(ArtifactImage).where(ArtifactImage.artifact_id == artifact.id)
            img_result = await db.execute(img_query)
            images = img_result.scalars().all()
            if len(images) < 4:
                stats["missing_images"] += 1

    return stats


async def main():
    parser = argparse.ArgumentParser(description="批量导入文物数据")
    parser.add_argument("--source", type=str, required=True, help="数据源文件路径")
    parser.add_argument("--format", type=str, default="auto", choices=["auto", "csv", "json"], help="文件格式")
    parser.add_argument("--batch-size", type=int, default=10, help="批量大小")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="跳过已存在的文物")
    parser.add_argument("--check", action="store_true", help="仅检查状态")
    args = parser.parse_args()

    if not os.path.exists(args.source):
        logger.error(f"文件不存在: {args.source}")
        return

    if args.check:
        stats = await check_import_status(args.source)
        logger.info(f"导入状态: {stats}")
        return

    # 自动检测格式
    fmt = args.format
    if fmt == "auto":
        if args.source.endswith('.csv'):
            fmt = "csv"
        elif args.source.endswith('.json'):
            fmt = "json"
        else:
            logger.error("无法自动检测格式，请使用 --format 指定")
            return

    logger.info(f"开始导入: {args.source}")

    # 初始化服务连接
    kg_service = get_kg_service()
    rag_service = get_rag_service()
    try:
        kg_service.connect()
        rag_service.connect()
    except Exception as e:
        logger.warning(f"服务连接失败: {e}")

    if fmt == "csv":
        stats = await import_from_csv(args.source, args.batch_size, args.skip_existing, kg_service, rag_service)
    else:
        stats = await import_from_json(args.source, args.batch_size, args.skip_existing, kg_service, rag_service)

    logger.info(f"导入完成: {stats}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
