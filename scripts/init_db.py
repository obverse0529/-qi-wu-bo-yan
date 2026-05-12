#!/usr/bin/env python3
"""
数据库初始化脚本
运行: python scripts/init_db.py
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.database import async_engine, Base, AsyncSessionLocal
from app.models.artifact import Artifact, ArtifactImage, ArtifactModel, ReconstructionTask, ArtifactStory


async def init_database():
    """创建所有数据库表"""
    print("正在创建数据库表...")

    async with async_engine.begin() as conn:
        # Drop all tables first (for development)
        await conn.run_sync(Base.metadata.drop_all)
        print("  - 已删除现有表")

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("  - 已创建所有表")

    print("数据库初始化完成!")


async def create_sample_data():
    """创建示例数据"""
    print("\n正在创建示例数据...")

    sample_artifacts = [
        {
            "name": "错金银四龙四凤铜方案座",
            "dynasty": "战国",
            "category": "青铜器",
            "dimensions": {"length": 54.8, "width": 52, "height": 35, "unit": "cm"},
            "description": "1977年出土于河北省平山县，采用了失蜡法铸造工艺，是研究战国时期中山国青铜冶铸水平的重要实物。",
        },
        {
            "name": "青釉凤鸟联珠纹扁壶（北朝）",
            "dynasty": "北朝",
            "category": "陶器",
            "dimensions": {"length": 30, "width": 15, "height": 35, "unit": "cm"},
            "description": "北方草原文化与中原文化交融的典型代表，造型独特，纹饰精美。",
        },
        {
            "name": "嵌绿松石金质虎形牌饰（战国）",
            "dynasty": "战国",
            "category": "金银器",
            "dimensions": {"length": 12, "width": 8, "height": 0.5, "unit": "cm"},
            "description": "采用金银错工艺，是战国时期金银器制作的杰出代表。",
        },
    ]

    async with AsyncSessionLocal() as session:
        for artifact_data in sample_artifacts:
            artifact = Artifact(**artifact_data)
            session.add(artifact)

        await session.commit()
        print(f"  - 已创建 {len(sample_artifacts)} 件示例文物")

    print("示例数据创建完成!")


async def main():
    await init_database()
    await create_sample_data()


if __name__ == "__main__":
    asyncio.run(main())
