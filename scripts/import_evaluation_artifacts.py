#!/usr/bin/env python3
r"""
评测集文物导入脚本
将 E:\博言\数据集\模型\ 目录下的41件文物GLB文件导入数据库

使用方法:
    python scripts/import_evaluation_artifacts.py --dry-run  # 预览不导入
    python scripts/import_evaluation_artifacts.py            # 正式导入
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, init_db
from app.models.artifact import Artifact, ArtifactModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 评测集GLB文件目录
EVAL_MODELS_DIR = Path(r"E:\博言\数据集\模型")


async def scan_evaluation_artifacts() -> list[dict]:
    """扫描评测集目录，返回文物信息列表"""
    artifacts = []

    try:
        for glb_path in sorted(EVAL_MODELS_DIR.glob("*.glb")):
            name = glb_path.stem  # 文件名（不含扩展名）
            artifacts.append({
                "name": name,
                "glb_path": str(glb_path),
                "glb_url": f"/uploads/models/{glb_path.name}",
            })
    except FileNotFoundError:
        logger.error(f"目录不存在: {EVAL_MODELS_DIR}")

    return artifacts


async def import_single_artifact(
    db: AsyncSession,
    artifact_data: dict,
    skip_existing: bool = True,
) -> tuple[str, str]:
    """
    导入单个文物

    Returns:
        (status, message): "imported", "skipped", or "error"
    """
    name = artifact_data["name"]

    # 检查是否已存在（按名称查重）
    if skip_existing:
        query = select(Artifact).where(Artifact.name == name)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            return "skipped", f"文物已存在: {name}"

    # 创建文物记录
    artifact = Artifact(
        name=name,
        dynasty="待考证",
        category="待分类",
        description=f"来自评测集的文物3D模型: {name}",
        extra_data={
            "source": "evaluation",
            "modelUrl": artifact_data["glb_url"],
            "modelPath": artifact_data["glb_path"],
        },
    )
    db.add(artifact)
    await db.flush()

    # 创建模型记录
    model = ArtifactModel(
        artifact_id=artifact.id,
        model_url=artifact_data["glb_url"],
        file_path=artifact_data["glb_path"],
        status="completed",
        has_texture=True,
        polygon_count=0,  # 未知
    )
    db.add(model)

    return "imported", name


async def import_all(
    dry_run: bool = False,
    skip_existing: bool = True,
) -> dict:
    """导入所有评测集文物"""
    stats = {"total": 0, "imported": 0, "skipped": 0, "errors": 0}
    errors = []

    # 扫描文物
    artifacts = await scan_evaluation_artifacts()
    stats["total"] = len(artifacts)

    if dry_run:
        logger.info(f"[DRY RUN] 将导入 {len(artifacts)} 件文物:")
        for a in artifacts:
            logger.info(f"  - {a['name']} -> {a['glb_url']}")
        return stats

    # 初始化数据库连接
    await init_db()

    # 批量导入
    async with AsyncSessionLocal() as db:
        for artifact_data in artifacts:
            try:
                status, msg = await import_single_artifact(
                    db, artifact_data, skip_existing
                )
                if status == "imported":
                    stats["imported"] += 1
                    logger.info(f"导入: {msg}")
                elif status == "skipped":
                    stats["skipped"] += 1
                    logger.info(f"跳过: {msg}")
            except Exception as e:
                stats["errors"] += 1
                error_msg = f"导入失败 {artifact_data['name']}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        if stats["errors"] == 0:
            await db.commit()
            logger.info("数据库提交成功")
        else:
            await db.rollback()
            logger.warning("数据库回滚（部分导入失败）")

    logger.info(f"导入完成: {stats}")
    if errors:
        logger.warning(f"错误列表: {errors}")

    return stats


async def verify_import() -> dict:
    """验证导入结果"""
    await init_db()

    async with AsyncSessionLocal() as db:
        query = select(Artifact)
        result = await db.execute(query)
        artifacts = result.scalars().all()

        stats = {
            "total_artifacts": len(artifacts),
            "artifacts_with_models": 0,
            "total_models": 0,
        }

        if not artifacts:
            logger.info(f"验证结果: {stats}")
            return stats

        # Batch fetch all models in one query
        artifact_ids = [a.id for a in artifacts]
        model_query = select(ArtifactModel).where(
            ArtifactModel.artifact_id.in_(artifact_ids)
        )
        model_result = await db.execute(model_query)
        all_models = model_result.scalars().all()

        # Group models by artifact_id
        models_by_artifact: dict = {}
        for model in all_models:
            models_by_artifact.setdefault(model.artifact_id, []).append(model)

        for artifact in artifacts:
            models = models_by_artifact.get(artifact.id, [])
            if models:
                stats["artifacts_with_models"] += 1
                stats["total_models"] += len(models)

    logger.info(f"验证结果: {stats}")
    return stats


async def main():
    parser = argparse.ArgumentParser(description="导入评测集文物")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际导入",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="跳过已存在的文物（默认开启）",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="仅验证当前导入状态",
    )
    args = parser.parse_args()

    if args.verify:
        await verify_import()
        return

    await import_all(dry_run=args.dry_run, skip_existing=args.skip_existing)


if __name__ == "__main__":
    asyncio.run(main())
