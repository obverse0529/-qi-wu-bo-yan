#!/usr/bin/env python3
"""
数据库和服务初始化脚本
运行: python scripts/init_services.py
"""

import asyncio
import sys
import os
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.database import async_engine, Base, AsyncSessionLocal
from app.models.artifact import Artifact, ArtifactImage, ArtifactModel, ReconstructionTask, ArtifactStory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_postgres():
    """初始化 PostgreSQL"""
    logger.info("正在初始化 PostgreSQL...")

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("  - 已删除现有表")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("  - 已创建所有表")

    logger.info("PostgreSQL 初始化完成")


async def init_neo4j():
    """初始化 Neo4j"""
    logger.info("正在初始化 Neo4j...")

    try:
        from app.services.kg_service import get_kg_service

        kg_service = get_kg_service()
        if kg_service.connect():
            stats = kg_service.get_statistics()
            logger.info(f"  - Neo4j 连接成功，节点统计: {stats}")
        else:
            logger.warning("  - Neo4j 连接失败，请检查服务是否启动")
    except Exception as e:
        logger.warning(f"  - Neo4j 初始化跳过: {e}")


async def init_milvus():
    """初始化 Milvus"""
    logger.info("正在初始化 Milvus...")

    try:
        from app.services.rag_service import get_rag_service

        rag_service = get_rag_service()
        if rag_service.connect():
            stats = rag_service.get_collection_stats()
            logger.info(f"  - Milvus 连接成功，集合统计: {stats}")
        else:
            logger.warning("  - Milvus 连接失败，请检查服务是否启动")
    except Exception as e:
        logger.warning(f"  - Milvus 初始化跳过: {e}")


async def create_sample_data():
    """创建示例数据"""
    logger.info("\n正在创建示例数据...")

    sample_artifacts = [
        {
            "name": "错金银四龙四凤铜方案座",
            "dynasty": "战国",
            "category": "青铜器",
            "dimensions": {"length": 54.8, "width": 52, "height": 35, "unit": "cm"},
            "description": "1977年出土于河北省平山县，采用了失蜡法铸造工艺，是研究战国时期中山国青铜冶铸水平的重要实物。",
            "metadata": {
                "techniques": ["失蜡法", "错金银"],
                "materials": ["青铜", "金", "银"],
                "site": "河北省平山县",
            },
        },
        {
            "name": "青釉凤鸟联珠纹扁壶（北朝）",
            "dynasty": "北朝",
            "category": "陶器",
            "dimensions": {"length": 30, "width": 15, "height": 35, "unit": "cm"},
            "description": "北方草原文化与中原文化交融的典型代表，造型独特，纹饰精美。",
            "metadata": {
                "techniques": ["青釉"],
                "materials": ["陶", "釉"],
                "site": "待考证",
            },
        },
        {
            "name": "嵌绿松石金质虎形牌饰（战国）",
            "dynasty": "战国",
            "category": "金银器",
            "dimensions": {"length": 12, "width": 8, "height": 0.5, "unit": "cm"},
            "description": "采用金银错工艺，是战国时期金银器制作的杰出代表。",
            "metadata": {
                "techniques": ["金银错", "镶嵌"],
                "materials": ["金", "绿松石"],
                "site": "待考证",
            },
        },
        {
            "name": "夹砂褐陶绳纹鬲",
            "dynasty": "商",
            "category": "陶器",
            "dimensions": {"length": 20, "width": 18, "height": 25, "unit": "cm"},
            "description": "商代典型炊具，夹砂褐陶质地，绳纹装饰。",
            "metadata": {
                "techniques": ["泥条盘筑", "绳纹装饰"],
                "materials": ["陶", "砂"],
                "site": "待考证",
            },
        },
        {
            "name": "兽面纹青铜甗",
            "dynasty": "商",
            "category": "青铜器",
            "dimensions": {"length": 35, "width": 25, "height": 45, "unit": "cm"},
            "description": "商代青铜礼器，兽面纹装饰，蒸食用具。",
            "metadata": {
                "techniques": ["青铜铸造", "兽面纹"],
                "materials": ["青铜"],
                "site": "待考证",
            },
        },
    ]

    async with AsyncSessionLocal() as session:
        for artifact_data in sample_artifacts:
            artifact = Artifact(**artifact_data)
            session.add(artifact)

        await session.commit()
        logger.info(f"  - 已创建 {len(sample_artifacts)} 件示例文物")

        # 为每件文物在 Neo4j 中创建图谱节点
        try:
            from app.services.kg_service import get_kg_service
            kg_service = get_kg_service()
            if kg_service.connect():
                for artifact_data in sample_artifacts:
                    # 获取刚插入的 artifact ID
                    result = await session.execute(
                        f"SELECT id FROM artifacts WHERE name = '{artifact_data['name']}'"
                    )
                    row = result.fetchone()
                    if row:
                        kg_service.build_from_artifact_data(
                            artifact_id=str(row[0]),
                            name=artifact_data["name"],
                            dynasty=artifact_data["dynasty"],
                            category=artifact_data["category"],
                            site=artifact_data.get("metadata", {}).get("site"),
                            techniques=artifact_data.get("metadata", {}).get("techniques", []),
                            materials=artifact_data.get("metadata", {}).get("materials", []),
                        )
                logger.info("  - 已为示例文物创建图谱节点")
        except Exception as e:
            logger.warning(f"  - 图谱节点创建跳过: {e}")

    logger.info("示例数据创建完成")


async def main():
    logger.info("=" * 50)
    logger.info("启物博言系统 - 数据库初始化")
    logger.info("=" * 50)

    # 1. 初始化 PostgreSQL
    await init_postgres()

    # 2. 初始化 Neo4j (可选)
    await init_neo4j()

    # 3. 初始化 Milvus (可选)
    await init_milvus()

    # 4. 创建示例数据
    await create_sample_data()

    logger.info("\n" + "=" * 50)
    logger.info("初始化完成!")
    logger.info("=" * 50)
    logger.info("\n启动服务:")
    logger.info("  后端: cd backend && uvicorn app.main:app --reload")
    logger.info("  前端: cd frontend && npm run dev")


if __name__ == "__main__":
    asyncio.run(main())
